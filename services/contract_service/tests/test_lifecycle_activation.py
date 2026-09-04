import os
import time
import unittest
from datetime import timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.contract_clock import contract_today
from app.core import scheduler as scheduler_module
from app.db.session import SessionLocal, engine
from app.models.contract import Contract
from app.models.contract_audit import ContractAudit
from app.models.contract_version import ContractVersion
from app.models.customer import Customer
from app.models.outbox_event import OutboxEvent
from app.services.contract_service import ContractService
from app.services.lifecycle_service import ContractLifecycleService


class LifecycleSchedulerTests(unittest.TestCase):
    def test_scheduler_runs_catch_up_immediately_on_startup(self):
        fake_scheduler = MagicMock()
        fake_scheduler.running = False
        call_order = []
        fake_scheduler.add_job.side_effect = (
            lambda *args, **kwargs: call_order.append("add_job")
        )
        fake_scheduler.start.side_effect = (
            lambda: call_order.append("start")
        )

        with (
            patch.object(scheduler_module, "scheduler", fake_scheduler),
            patch.object(
                scheduler_module,
                "run_contract_lifecycle",
                side_effect=lambda: call_order.append("catch_up"),
            ),
        ):
            scheduler_module.start_scheduler()

        self.assertEqual(call_order, ["catch_up", "add_job", "start"])
        self.assertEqual(
            fake_scheduler.add_job.call_args.kwargs["seconds"],
            settings.CONTRACT_LIFECYCLE_INTERVAL_SECONDS,
        )

    def test_run_once_skips_when_another_process_holds_lock(self):
        db = MagicMock()
        db.execute.return_value.scalar.return_value = False
        connection = MagicMock()

        with (
            patch(
                "app.services.lifecycle_service.engine.connect",
                return_value=connection,
            ),
            patch(
                "app.services.lifecycle_service.Session",
                return_value=db,
            ),
        ):
            result = ContractLifecycleService.run_once()

        self.assertTrue(result["skipped"])
        db.close.assert_called_once_with()
        connection.close.assert_called_once_with()


@unittest.skipUnless(
    os.getenv("RUN_CONTRACT_INTEGRATION_TESTS") == "1",
    "set RUN_CONTRACT_INTEGRATION_TESTS=1 to use the Contract PostgreSQL database",
)
class LifecycleActivationIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.connection = engine.connect()
        self.outer_transaction = self.connection.begin()
        self.db = Session(
            bind=self.connection,
            join_transaction_mode="create_savepoint",
        )

        self.staff_id = uuid4()
        self.customer = Customer(
            customer_code=f"LIFE-{uuid4().hex[:12]}",
            tax_code=f"LIFE-TAX-{uuid4().hex[:12]}",
            company_name="Lifecycle activation test",
            status="ACTIVE",
        )
        self.db.add(self.customer)
        self.db.flush()

    def tearDown(self):
        self.db.close()
        if self.outer_transaction.is_active:
            self.outer_transaction.rollback()
        self.connection.close()

    def create_contract(self, effective_from):
        contract = Contract(
            contract_number=f"CTR-LIFE-{uuid4().hex[:12]}",
            customer_id=self.customer.customer_id,
            current_version=1,
            status="APPROVED",
            row_version=1,
        )
        self.db.add(contract)
        self.db.flush()

        self.db.add(
            ContractVersion(
                contract_id=contract.contract_id,
                version_no=1,
                effective_from=effective_from,
                effective_to=effective_from + timedelta(days=365),
                contract_value=Decimal("1000000.00"),
                payment_terms="Lifecycle payment terms",
                service_terms="Lifecycle service terms",
                created_by=self.staff_id,
                change_reason="Lifecycle integration test",
            )
        )
        self.db.flush()
        return contract.contract_id

    def test_due_contracts_are_drained_and_activation_is_idempotent(self):
        today = contract_today()
        overdue_id = self.create_contract(today - timedelta(days=1))
        today_id = self.create_contract(today)
        future_id = self.create_contract(today + timedelta(days=1))
        simultaneous_ids = [
            self.create_contract(today)
            for _ in range(4)
        ]
        due_ids = [overdue_id, today_id, *simultaneous_ids]
        self.db.commit()

        activated = ContractLifecycleService.process_activations(
            db=self.db,
            today=today,
            batch_size=2,
        )

        self.assertEqual(activated, len(due_ids))
        self.db.expire_all()
        statuses = {
            contract.contract_id: contract.status
            for contract in self.db.query(Contract)
            .filter(Contract.contract_id.in_([*due_ids, future_id]))
            .all()
        }
        self.assertTrue(
            all(statuses[contract_id] == "ACTIVE" for contract_id in due_ids)
        )
        self.assertEqual(statuses[future_id], "APPROVED")

        audit_count = (
            self.db.query(ContractAudit)
            .filter(
                ContractAudit.contract_id.in_(due_ids),
                ContractAudit.action == "ACTIVATE",
            )
            .count()
        )
        event_count = (
            self.db.query(OutboxEvent)
            .filter(
                OutboxEvent.aggregate_id.in_(due_ids),
                OutboxEvent.event_type == "CONTRACT_ACTIVATED",
            )
            .count()
        )
        self.assertEqual(audit_count, len(due_ids))
        self.assertEqual(event_count, len(due_ids))

        # Simulate both a stale concurrent selection and the next scheduled run.
        ContractService.activate_contract(self.db, overdue_id)
        self.assertEqual(
            ContractLifecycleService.process_activations(
                db=self.db,
                today=today,
                batch_size=2,
            ),
            0,
        )
        self.assertEqual(
            self.db.query(ContractAudit)
            .filter(
                ContractAudit.contract_id.in_(due_ids),
                ContractAudit.action == "ACTIVATE",
            )
            .count(),
            audit_count,
        )
        self.assertEqual(
            self.db.query(OutboxEvent)
            .filter(
                OutboxEvent.aggregate_id.in_(due_ids),
                OutboxEvent.event_type == "CONTRACT_ACTIVATED",
            )
            .count(),
            event_count,
        )

    def test_postgres_advisory_lock_allows_only_one_worker(self):
        first = SessionLocal()
        second = SessionLocal()

        try:
            first_acquired = False
            for _ in range(100):
                first_acquired = bool(
                    first.execute(
                        text("SELECT pg_try_advisory_lock(:lock_id)"),
                        {"lock_id": ContractLifecycleService.ADVISORY_LOCK_ID},
                    ).scalar()
                )
                if first_acquired:
                    break
                time.sleep(0.02)

            second_acquired = bool(
                second.execute(
                    text("SELECT pg_try_advisory_lock(:lock_id)"),
                    {"lock_id": ContractLifecycleService.ADVISORY_LOCK_ID},
                ).scalar()
            )

            self.assertTrue(first_acquired)
            self.assertFalse(second_acquired)
        finally:
            first.execute(
                text("SELECT pg_advisory_unlock(:lock_id)"),
                {"lock_id": ContractLifecycleService.ADVISORY_LOCK_ID},
            )
            first.commit()
            first.close()
            second.close()
