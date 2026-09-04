import os
import unittest
from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.contract_clock import contract_today
from app.db.session import engine
from app.models.contract import Contract
from app.models.contract_attachment import ContractAttachment
from app.models.contract_audit import ContractAudit
from app.models.contract_version import ContractVersion
from app.models.customer import Customer
from app.models.outbox_event import OutboxEvent
from app.services.approval_service import ApprovalService
from app.services.contract_service import ContractService


@unittest.skipUnless(
    os.getenv("RUN_CONTRACT_INTEGRATION_TESTS") == "1",
    "set RUN_CONTRACT_INTEGRATION_TESTS=1 to use the Contract PostgreSQL database",
)
class ContractOutboxEventIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.connection = engine.connect()
        self.outer_transaction = self.connection.begin()
        self.db = Session(
            bind=self.connection,
            join_transaction_mode="create_savepoint",
        )
        self.staff_id = uuid4()
        self.manager_id = uuid4()
        self.director_id = uuid4()

        customer = Customer(
            customer_code=f"EVENT-{uuid4().hex[:12]}",
            tax_code=f"EVENT-TAX-{uuid4().hex[:12]}",
            company_name="Contract event test",
            status="ACTIVE",
        )
        self.db.add(customer)
        self.db.flush()

        self.contract = Contract(
            contract_number=f"CTR-EVENT-{uuid4().hex[:12]}",
            customer_id=customer.customer_id,
            current_version=1,
            status="DRAFT",
            row_version=1,
        )
        self.db.add(self.contract)
        self.db.flush()

        effective_from = contract_today() + timedelta(days=1)
        version = ContractVersion(
            contract_id=self.contract.contract_id,
            version_no=1,
            effective_from=effective_from,
            effective_to=effective_from + timedelta(days=365),
            contract_value=Decimal("1000000.00"),
            payment_terms="Event payment terms",
            service_terms="Event service terms",
            created_by=self.staff_id,
            change_reason="Event integration test",
        )
        self.db.add(version)
        self.db.flush()

        attachment_id = uuid4()
        self.db.add(
            ContractAttachment(
                attachment_id=attachment_id,
                version_id=version.version_id,
                file_name="contract.pdf",
                object_key=(
                    f"event-tests/{self.contract.contract_id}/"
                    f"{version.version_id}/{attachment_id}"
                ),
                content_type="application/pdf",
                file_size=1,
                uploaded_by=self.staff_id,
            )
        )
        self.db.commit()

    def tearDown(self):
        self.db.close()
        if self.outer_transaction.is_active:
            self.outer_transaction.rollback()
        self.connection.close()

    def submit(self):
        ContractService.submit_contract(
            db=self.db,
            contract_id=self.contract.contract_id,
            idempotency_key=f"event-submit-{uuid4()}",
            actor_id=self.staff_id,
            actor_role="STAFF",
        )
        self.db.refresh(self.contract)

    def start_manager_review(self):
        ApprovalService.start_review(
            self.db,
            self.contract.contract_id,
            self.manager_id,
            "MANAGER",
        )
        self.db.refresh(self.contract)

    def approve_by_manager(self):
        ApprovalService.approve(
            self.db,
            self.contract.contract_id,
            self.manager_id,
            "MANAGER",
            "Manager comment must remain outside Kafka payload",
        )
        self.db.refresh(self.contract)

    def start_director_review(self):
        ApprovalService.start_review(
            self.db,
            self.contract.contract_id,
            self.director_id,
            "DIRECTOR",
        )
        self.db.refresh(self.contract)

    def assert_action_event(
        self,
        event_type,
        audit_action,
        actor_id,
        actor_role,
        expected_status,
        approval_round=None,
    ):
        event = (
            self.db.query(OutboxEvent)
            .filter(
                OutboxEvent.aggregate_id == self.contract.contract_id,
                OutboxEvent.event_type == event_type,
            )
            .one()
        )
        envelope = event.payload
        payload = envelope["payload"]

        self.assertEqual(envelope["event_name"], event_type)
        self.assertEqual(payload["contract_id"], str(self.contract.contract_id))
        self.assertEqual(payload["contract_number"], self.contract.contract_number)
        self.assertEqual(payload["customer_id"], str(self.contract.customer_id))
        self.assertEqual(payload["current_version"], self.contract.current_version)
        self.assertEqual(payload["status"], expected_status)
        self.assertEqual(payload["actor_id"], str(actor_id))
        self.assertEqual(payload["actor_role"], actor_role)

        if approval_round is None:
            self.assertNotIn("approval_round", payload)
        else:
            self.assertEqual(payload["approval_round"], approval_round)

        for forbidden_field in (
            "reason",
            "director_reason",
            "comment",
        ):
            self.assertNotIn(forbidden_field, payload)

        self.assertEqual(
            self.db.query(ContractAudit)
            .filter(
                ContractAudit.contract_id == self.contract.contract_id,
                ContractAudit.action == audit_action,
            )
            .count(),
            1,
        )

    def test_submit_manager_approve_and_director_approve_events(self):
        self.submit()
        self.assert_action_event(
            "CONTRACT_SUBMITTED",
            "SUBMIT",
            self.staff_id,
            "STAFF",
            "SUBMITTED",
        )

        self.start_manager_review()
        self.approve_by_manager()
        self.assert_action_event(
            "CONTRACT_MANAGER_APPROVED",
            "MANAGER_APPROVE",
            self.manager_id,
            "MANAGER",
            "DIRECTOR_REVIEW",
            approval_round=1,
        )

        self.start_director_review()
        ApprovalService.approve(
            self.db,
            self.contract.contract_id,
            self.director_id,
            "DIRECTOR",
            "Director comment must remain outside Kafka payload",
        )
        self.assert_action_event(
            "CONTRACT_DIRECTOR_APPROVED",
            "DIRECTOR_APPROVE",
            self.director_id,
            "DIRECTOR",
            "APPROVED",
            approval_round=1,
        )

    def test_manager_reject_event(self):
        self.submit()
        self.start_manager_review()
        ApprovalService.reject(
            self.db,
            self.contract.contract_id,
            self.manager_id,
            "MANAGER",
            "Manager rejection reason",
        )
        self.assert_action_event(
            "CONTRACT_MANAGER_REJECTED",
            "MANAGER_REJECT",
            self.manager_id,
            "MANAGER",
            "REJECTED",
            approval_round=1,
        )

    def test_director_reject_event(self):
        self.submit()
        self.start_manager_review()
        self.approve_by_manager()
        self.start_director_review()
        ApprovalService.reject(
            self.db,
            self.contract.contract_id,
            self.director_id,
            "DIRECTOR",
            "Director rejection reason",
        )
        self.assert_action_event(
            "CONTRACT_DIRECTOR_REJECTED",
            "DIRECTOR_REJECT",
            self.director_id,
            "DIRECTOR",
            "REJECTED",
            approval_round=1,
        )

    def test_manager_revision_requested_event(self):
        self.submit()
        self.start_manager_review()
        ApprovalService.request_revision(
            self.db,
            self.contract.contract_id,
            self.manager_id,
            "MANAGER",
            "Manager revision reason",
        )
        self.assert_action_event(
            "CONTRACT_MANAGER_REVISION_REQUESTED",
            "MANAGER_REQUEST_REVISION",
            self.manager_id,
            "MANAGER",
            "REVISION_REQUESTED",
            approval_round=1,
        )

    def test_director_revision_and_manager_send_events(self):
        self.submit()
        self.start_manager_review()
        self.approve_by_manager()
        self.start_director_review()
        ApprovalService.request_revision(
            self.db,
            self.contract.contract_id,
            self.director_id,
            "DIRECTOR",
            "Director revision reason",
        )
        self.assert_action_event(
            "CONTRACT_DIRECTOR_REVISION_REQUESTED",
            "DIRECTOR_REQUEST_REVISION",
            self.director_id,
            "DIRECTOR",
            "DIRECTOR_REVIEW",
            approval_round=1,
        )

        ApprovalService.manager_send_revision(
            self.db,
            self.contract.contract_id,
            self.manager_id,
            "MANAGER",
            "Manager revision reason for Staff",
        )
        self.assert_action_event(
            "CONTRACT_MANAGER_SEND_REVISION",
            "MANAGER_SEND_REVISION",
            self.manager_id,
            "MANAGER",
            "REVISION_REQUESTED",
            approval_round=1,
        )


if __name__ == "__main__":
    unittest.main()
