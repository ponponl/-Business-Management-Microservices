import unittest
from unittest.mock import Mock

from consumers.notification_consumer import process_event


EXPECTED_RECIPIENTS = {
    "CONTRACT_SUBMITTED": {2},
    "CONTRACT_MANAGER_APPROVED": {1, 3},
    "CONTRACT_MANAGER_REJECTED": {1},
    "CONTRACT_MANAGER_REVISION_REQUESTED": {1},
    "CONTRACT_DIRECTOR_APPROVED": {1, 2},
    "CONTRACT_DIRECTOR_REJECTED": {1, 2},
    "CONTRACT_DIRECTOR_REVISION_REQUESTED": {1, 2},
    "CONTRACT_MANAGER_SEND_REVISION": {1},
}


class EmptyQuery:
    def filter(self, *args):
        return self

    def first(self):
        return None


class ExistingQuery(EmptyQuery):
    def first(self):
        return object()


class NotificationRecipientTests(unittest.TestCase):
    def test_contract_events_create_notifications_only_for_mapped_roles(self):
        for event_type, expected_user_ids in EXPECTED_RECIPIENTS.items():
            with self.subTest(event_type=event_type):
                db = Mock()
                db.query.return_value = EmptyQuery()

                process_event(
                    topic="contract.events",
                    event_data={
                        "event_type": event_type,
                        "payload": {"contract_number": "CTR-TEST"},
                    },
                    db=db,
                    event_id=f"event-{event_type}",
                )

                notifications = [
                    call.args[0]
                    for call in db.add.call_args_list
                ]
                actual_user_ids = {
                    notification.user_id
                    for notification in notifications
                }

                self.assertEqual(actual_user_ids, expected_user_ids)
                self.assertEqual(len(notifications), len(expected_user_ids))
                self.assertEqual(
                    {notification.event_id for notification in notifications},
                    {
                        f"event-{event_type}-{user_id}"
                        for user_id in expected_user_ids
                    },
                )
                db.commit.assert_called_once_with()

    def test_existing_recipient_event_remains_idempotent(self):
        db = Mock()
        db.query.return_value = ExistingQuery()

        process_event(
            topic="contract.events",
            event_data={
                "event_type": "CONTRACT_SUBMITTED",
                "payload": {"contract_number": "CTR-TEST"},
            },
            db=db,
            event_id="contract.events-0-42",
        )

        db.add.assert_not_called()
        db.commit.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
