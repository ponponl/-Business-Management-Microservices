import asyncio
import os
import tempfile
import unittest
from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy.orm import Session
from starlette.datastructures import Headers

from app.db.session import engine
from app.models.contract import Contract
from app.models.contract_approval import ContractApproval
from app.models.contract_attachment import ContractAttachment
from app.models.contract_version import ContractVersion
from app.models.customer import Customer
from app.schemas.contract import (
    ContractListResponse,
    ContractResponse,
    UpdateContractRequest,
)
from app.services.approval_service import ApprovalService
from app.services.contract_service import ContractService
from app.services.file_storage import storage
from app.services.revision_context import get_current_approval_metadata
from app.utils.attachment import build_attachment_object_key


@unittest.skipUnless(
    os.getenv("RUN_CONTRACT_INTEGRATION_TESTS") == "1",
    "set RUN_CONTRACT_INTEGRATION_TESTS=1 to use the Contract PostgreSQL database",
)
class RevisionWorkflowIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.connection = engine.connect()
        self.outer_transaction = self.connection.begin()
        self.db = Session(
            bind=self.connection,
            join_transaction_mode="create_savepoint",
        )
        self.temp_storage = tempfile.TemporaryDirectory()
        self.original_storage_path = storage.base_path
        storage.base_path = Path(self.temp_storage.name)

        self.staff_id = uuid4()
        self.manager_id = uuid4()
        self.director_id = uuid4()
        self.effective_from = date.today() + timedelta(days=1)
        self.effective_to = self.effective_from + timedelta(days=365)

        customer = Customer(
            customer_code=f"TEST-{uuid4().hex[:12]}",
            tax_code=f"TAX-{uuid4().hex[:12]}",
            company_name="Revision workflow test",
            status="ACTIVE",
        )
        self.db.add(customer)
        self.db.flush()

        self.contract = Contract(
            contract_number=f"CTR-TEST-{uuid4().hex[:12]}",
            customer_id=customer.customer_id,
            current_version=1,
            status="DRAFT",
            row_version=1,
        )
        self.db.add(self.contract)
        self.db.flush()

        version = ContractVersion(
            contract_id=self.contract.contract_id,
            version_no=1,
            effective_from=date(2026, 1, 1),
            effective_to=date(2026, 12, 31),
            contract_value=Decimal("1000000.00"),
            payment_terms="Initial payment terms",
            service_terms="Initial service terms",
            created_by=self.staff_id,
            change_reason="Integration test",
        )
        self.db.add(version)
        self.db.flush()
        self.initial_version_id = version.version_id

        attachment_id = uuid4()
        self.initial_attachment_id = attachment_id
        object_key = build_attachment_object_key(
            self.contract.contract_id,
            version.version_id,
            attachment_id,
        )
        storage.save(b"contract-test", object_key)
        self.db.add(
            ContractAttachment(
                attachment_id=attachment_id,
                version_id=version.version_id,
                file_name="contract.pdf",
                object_key=object_key,
                content_type="application/pdf",
                file_size=13,
                uploaded_by=self.staff_id,
            )
        )

        second_attachment_id = uuid4()
        self.second_attachment_id = second_attachment_id
        second_object_key = build_attachment_object_key(
            self.contract.contract_id,
            version.version_id,
            second_attachment_id,
        )
        storage.save(b"terms-test", second_object_key)
        self.db.add(
            ContractAttachment(
                attachment_id=second_attachment_id,
                version_id=version.version_id,
                file_name="terms.pdf",
                object_key=second_object_key,
                content_type="application/pdf",
                file_size=10,
                uploaded_by=self.staff_id,
            )
        )
        self.db.commit()

    def tearDown(self):
        self.db.close()
        if self.outer_transaction.is_active:
            self.outer_transaction.rollback()
        self.connection.close()
        storage.base_path = self.original_storage_path
        self.temp_storage.cleanup()

    def update_contract(self, payment_terms):
        request = UpdateContractRequest(
            effective_from=self.effective_from,
            effective_to=self.effective_to,
            contract_value=Decimal("1000000.00"),
            payment_terms=payment_terms,
            service_terms="Updated service terms",
            row_version=self.contract.row_version,
        )
        asyncio.run(
            ContractService.update_contract(
                db=self.db,
                contract_id=self.contract.contract_id,
                request=request,
                actor_id=self.staff_id,
                attachments=[],
            )
        )
        self.db.refresh(self.contract)

    def submit(self, key):
        first = ContractService.submit_contract(
            db=self.db,
            contract_id=self.contract.contract_id,
            idempotency_key=key,
            actor_id=self.staff_id,
            actor_role="STAFF",
        )
        replay = ContractService.submit_contract(
            db=self.db,
            contract_id=self.contract.contract_id,
            idempotency_key=key,
            actor_id=self.staff_id,
            actor_role="STAFF",
        )
        self.assertEqual(first, replay)
        self.db.refresh(self.contract)

    def update_attachments(self, removed_attachment_ids=None, new_file_name=None):
        request = UpdateContractRequest(
            effective_from=self.effective_from,
            effective_to=self.effective_to,
            contract_value=Decimal("1000000.00"),
            payment_terms="Attachment selection update",
            service_terms="Updated service terms",
            row_version=self.contract.row_version,
            removed_attachment_ids=removed_attachment_ids or [],
        )

        attachments = []
        if new_file_name:
            attachments.append(
                UploadFile(
                    file=BytesIO(b"new-contract-file"),
                    filename=new_file_name,
                    headers=Headers({"content-type": "application/pdf"}),
                )
            )

        response = asyncio.run(
            ContractService.update_contract(
                db=self.db,
                contract_id=self.contract.contract_id,
                request=request,
                actor_id=self.staff_id,
                attachments=attachments,
            )
        )

        return {attachment.file_name for attachment in response["attachments"]}

    def test_update_keeps_all_existing_attachments(self):
        self.assertEqual(
            self.update_attachments(),
            {"contract.pdf", "terms.pdf"},
        )

    def test_update_removes_one_and_keeps_the_other_attachment(self):
        self.assertEqual(
            self.update_attachments([self.initial_attachment_id]),
            {"terms.pdf"},
        )

    def test_update_removes_all_existing_attachments(self):
        self.assertEqual(
            self.update_attachments(
                [self.initial_attachment_id, self.second_attachment_id]
            ),
            set(),
        )

        self.assertEqual(
            self.db.query(ContractAttachment)
            .filter(ContractAttachment.version_id == self.initial_version_id)
            .count(),
            2,
        )

    def test_update_keeps_existing_and_adds_new_attachment(self):
        self.assertEqual(
            self.update_attachments(new_file_name="new.pdf"),
            {"contract.pdf", "terms.pdf", "new.pdf"},
        )

    def test_update_removes_existing_and_adds_new_attachment(self):
        self.assertEqual(
            self.update_attachments(
                [self.initial_attachment_id],
                new_file_name="new.pdf",
            ),
            {"terms.pdf", "new.pdf"},
        )

    def test_manager_and_director_revision_rounds_end_to_end(self):
        self.submit(f"submit-{uuid4()}")
        ApprovalService.start_review(
            self.db, self.contract.contract_id, self.manager_id, "MANAGER"
        )
        ApprovalService.request_revision(
            self.db,
            self.contract.contract_id,
            self.manager_id,
            "MANAGER",
            "Manager direct reason",
        )

        metadata = ContractService.get_current_revision_metadata(
            self.db, self.contract
        )
        self.assertEqual(self.contract.status, "REVISION_REQUESTED")
        self.assertEqual(
            metadata["revision_reason_for_staff"], "Manager direct reason"
        )

        self.update_contract("Updated after Manager revision")
        self.assertEqual(self.contract.status, "REVISION_REQUESTED")
        current_version = ContractService.get_contract(
            self.db, self.contract.contract_id
        )[1]
        self.assertEqual(len(current_version.attachments), 2)

        self.submit(f"submit-{uuid4()}")
        ApprovalService.start_review(
            self.db, self.contract.contract_id, self.manager_id, "MANAGER"
        )
        self.assertEqual(self.contract.status, "MANAGER_REVIEW")
        self.assertEqual(
            ContractService.get_current_revision_metadata(
                self.db, self.contract
            )["revision_reason_for_manager"],
            "Manager direct reason",
        )

        ApprovalService.approve(
            self.db, self.contract.contract_id, self.manager_id, "MANAGER"
        )
        ApprovalService.start_review(
            self.db, self.contract.contract_id, self.director_id, "DIRECTOR"
        )
        ApprovalService.start_review(
            self.db, self.contract.contract_id, self.director_id, "DIRECTOR"
        )
        ApprovalService.request_revision(
            self.db,
            self.contract.contract_id,
            self.director_id,
            "DIRECTOR",
            "Director reason",
        )

        self.db.refresh(self.contract)
        metadata = ContractService.get_current_revision_metadata(
            self.db, self.contract
        )
        self.assertEqual(self.contract.status, "DIRECTOR_REVIEW")
        self.assertEqual(
            get_current_approval_metadata(self.contract)["director_approval_status"],
            "REVISION_REQUESTED",
        )
        self.assertEqual(metadata["revision_reason_for_manager"], "Director reason")
        self.assertIsNone(metadata["revision_reason_for_staff"])
        self.assertEqual(metadata["revision_reason_for_director"], "Director reason")

        items, total, summary = ContractService.list_contracts(
            self.db,
            customer_id=self.contract.customer_id,
            limit=100,
        )
        list_response = ContractListResponse.model_validate(
            {
                "items": items,
                "total": total,
                "skip": 0,
                "limit": 100,
                "summary": summary,
            }
        )
        list_item = next(
            item
            for item in list_response.items
            if item.contract_id == self.contract.contract_id
        )
        self.assertEqual(list_item.status, "DIRECTOR_REVIEW")
        self.assertEqual(list_item.director_approval_status, "REVISION_REQUESTED")
        self.assertEqual(list_item.revision_reason_for_manager, "Director reason")

        ApprovalService.manager_send_revision(
            self.db,
            self.contract.contract_id,
            self.manager_id,
            "MANAGER",
            "Manager reason for Staff",
        )
        self.db.refresh(self.contract)
        metadata = ContractService.get_current_revision_metadata(
            self.db, self.contract
        )
        self.assertEqual(self.contract.status, "REVISION_REQUESTED")
        self.assertEqual(
            metadata["revision_reason_for_staff"], "Manager reason for Staff"
        )
        self.assertEqual(
            metadata["revision_reason_for_manager"], "Manager reason for Staff"
        )
        self.assertEqual(metadata["revision_reason_for_director"], "Director reason")

        current_version = ContractService.get_contract(
            self.db, self.contract.contract_id
        )[1]
        detail_response = ContractResponse.model_validate(
            ContractService.build_contract_response(
                contract=self.contract,
                version=current_version,
                attachments=current_version.attachments,
            )
        )
        self.assertEqual(
            detail_response.revision_reason_for_staff,
            "Manager reason for Staff",
        )

        self.update_contract("Updated after Director revision")
        self.submit(f"submit-{uuid4()}")
        ApprovalService.start_review(
            self.db, self.contract.contract_id, self.manager_id, "MANAGER"
        )

        self.db.refresh(self.contract)
        approval_metadata = get_current_approval_metadata(self.contract)
        self.assertEqual(self.contract.status, "MANAGER_REVIEW")
        self.assertEqual(approval_metadata["current_approval_round"], 3)
        self.assertIsNone(approval_metadata["director_approval_status"])

        ApprovalService.approve(
            self.db, self.contract.contract_id, self.manager_id, "MANAGER"
        )
        self.db.refresh(self.contract)
        self.assertEqual(self.contract.status, "DIRECTOR_REVIEW")
        self.assertEqual(
            ContractService.get_current_revision_metadata(
                self.db, self.contract
            )["revision_reason_for_director"],
            "Director reason",
        )

        approvals = (
            self.db.query(ContractApproval)
            .filter(ContractApproval.contract_id == self.contract.contract_id)
            .all()
        )
        round_steps = [
            (item.approval_round, item.step_no)
            for item in approvals
        ]
        self.assertEqual(len(round_steps), len(set(round_steps)))


if __name__ == "__main__":
    unittest.main()
