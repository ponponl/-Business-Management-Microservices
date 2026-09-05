import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

from app.schemas.contract import CancelContractRequest
from app.services.contract_service import ContractService
from app.services.state_machine import ContractStateMachine, ContractStatus


class ContractCancelPolicyTests(unittest.TestCase):
    def test_revision_requested_has_no_cancel_transition(self):
        self.assertFalse(
            ContractStateMachine.can_transition(
                ContractStatus.REVISION_REQUESTED,
                "cancel",
            )
        )

    def test_existing_cancel_transitions_remain_available(self):
        for status in (ContractStatus.DRAFT, ContractStatus.SUBMITTED):
            with self.subTest(status=status):
                self.assertTrue(
                    ContractStateMachine.can_transition(status, "cancel")
                )

    @patch(
        "app.services.contract_service.ContractRepository.get_by_id_for_update"
    )
    def test_service_rejects_cancel_for_revision_requested(self, get_contract):
        get_contract.return_value = SimpleNamespace(status="REVISION_REQUESTED")
        db = Mock()

        with self.assertRaisesRegex(ValueError, "CANCEL_NOT_ALLOWED"):
            ContractService.cancel_contract(
                db=db,
                contract_id=uuid4(),
                request=CancelContractRequest(reason="No longer needed"),
                actor_id=uuid4(),
            )

        db.rollback.assert_called_once_with()
        db.commit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
