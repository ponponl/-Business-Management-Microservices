import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.services.revision_context import (
    DIRECTOR_REQUEST_REVISION,
    MANAGER_REQUEST_REVISION,
    MANAGER_SEND_REVISION,
    get_current_approval_metadata,
    get_revision_metadata,
)


BASE_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)


def approval(approval_round, step_no, status, minute):
    timestamp = BASE_TIME + timedelta(minutes=minute)
    return SimpleNamespace(
        approval_id=uuid4(),
        approval_round=approval_round,
        step_no=step_no,
        status=status,
        created_at=timestamp,
        updated_at=timestamp,
    )


def audit(action, note, minute):
    return SimpleNamespace(
        audit_id=uuid4(),
        action=action,
        note=note,
        created_at=BASE_TIME + timedelta(minutes=minute),
    )


def contract(approvals, audits):
    return SimpleNamespace(
        approval_records=approvals,
        audits=audits,
    )


class RevisionContextTests(unittest.TestCase):
    def test_manager_revision_remains_visible_during_next_review_round(self):
        item = contract(
            approvals=[
                approval(1, 1, "REVISION_REQUESTED", 1),
                approval(2, 1, "PENDING", 5),
            ],
            audits=[
                audit(MANAGER_REQUEST_REVISION, "Manager reason", 2),
                audit("UPDATE", "Staff update", 3),
                audit("SUBMIT", "Staff submit", 4),
            ],
        )

        metadata = get_revision_metadata(item)

        self.assertEqual(metadata["revision_round"], 1)
        self.assertEqual(metadata["revision_reason_for_staff"], "Manager reason")
        self.assertEqual(metadata["revision_reason_for_manager"], "Manager reason")
        self.assertIsNone(metadata["revision_reason_for_director"])

    def test_director_revision_maps_reasons_by_viewer(self):
        item = contract(
            approvals=[
                approval(2, 1, "APPROVED", 1),
                approval(2, 2, "REVISION_REQUESTED", 2),
            ],
            audits=[
                audit(DIRECTOR_REQUEST_REVISION, "Director reason", 3),
                audit(MANAGER_SEND_REVISION, "Manager reason for Staff", 4),
            ],
        )

        metadata = get_revision_metadata(item)

        self.assertEqual(metadata["revision_round"], 2)
        self.assertEqual(metadata["revision_reason_for_staff"], "Manager reason for Staff")
        self.assertEqual(metadata["revision_reason_for_manager"], "Manager reason for Staff")
        self.assertEqual(metadata["revision_reason_for_director"], "Director reason")

    def test_manager_sees_director_reason_before_send(self):
        item = contract(
            approvals=[
                approval(3, 1, "APPROVED", 1),
                approval(3, 2, "REVISION_REQUESTED", 2),
            ],
            audits=[
                audit(DIRECTOR_REQUEST_REVISION, "Latest Director reason", 3),
            ],
        )

        metadata = get_revision_metadata(item)

        self.assertIsNone(metadata["revision_reason_for_staff"])
        self.assertEqual(metadata["revision_reason_for_manager"], "Latest Director reason")
        self.assertEqual(metadata["revision_reason_source_for_manager"], "DIRECTOR")

    def test_old_director_approval_does_not_leak_into_new_round(self):
        item = contract(
            approvals=[
                approval(2, 1, "APPROVED", 1),
                approval(2, 2, "REVISION_REQUESTED", 2),
                approval(3, 1, "PENDING", 6),
            ],
            audits=[],
        )

        metadata = get_current_approval_metadata(item)

        self.assertEqual(metadata["current_approval_round"], 3)
        self.assertIsNone(metadata["director_approval_status"])


if __name__ == "__main__":
    unittest.main()
