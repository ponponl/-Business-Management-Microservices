import unittest
from datetime import date, timedelta
from uuid import uuid4

from pydantic import ValidationError

from app.schemas.contract import CreateContractRequest, UpdateContractRequest


class ContractValidationTests(unittest.TestCase):
    def valid_payload(self):
        effective_from = date.today() + timedelta(days=1)
        return {
            "effective_from": effective_from,
            "effective_to": effective_from + timedelta(days=30),
            "contract_value": 1000000,
            "payment_terms": "Thanh toán trong 30 ngày",
            "service_terms": "Điều khoản vận chuyển",
        }

    def payload_for(self, schema):
        payload = self.valid_payload()
        if schema is CreateContractRequest:
            payload["customer_id"] = uuid4()
        else:
            payload["row_version"] = 1
        return payload

    def test_create_and_update_require_payment_terms(self):
        for schema in (CreateContractRequest, UpdateContractRequest):
            with self.subTest(schema=schema.__name__):
                payload = self.payload_for(schema)
                payload["payment_terms"] = "   "
                with self.assertRaises(ValidationError):
                    schema.model_validate(payload)

    def test_create_and_update_require_service_terms(self):
        for schema in (CreateContractRequest, UpdateContractRequest):
            with self.subTest(schema=schema.__name__):
                payload = self.payload_for(schema)
                payload["service_terms"] = "   "
                with self.assertRaises(ValidationError):
                    schema.model_validate(payload)

    def test_create_and_update_reject_past_start_date(self):
        for schema in (CreateContractRequest, UpdateContractRequest):
            with self.subTest(schema=schema.__name__):
                payload = self.payload_for(schema)
                payload["effective_from"] = date.today() - timedelta(days=1)
                with self.assertRaises(ValidationError):
                    schema.model_validate(payload)

    def test_create_and_update_require_end_after_start(self):
        for schema in (CreateContractRequest, UpdateContractRequest):
            with self.subTest(schema=schema.__name__):
                payload = self.payload_for(schema)
                payload["effective_to"] = payload["effective_from"]
                with self.assertRaises(ValidationError):
                    schema.model_validate(payload)

    def test_create_and_update_accept_valid_payload(self):
        for schema in (CreateContractRequest, UpdateContractRequest):
            with self.subTest(schema=schema.__name__):
                validated = schema.model_validate(self.payload_for(schema))
                self.assertLess(validated.effective_from, validated.effective_to)


if __name__ == "__main__":
    unittest.main()
