from sqlalchemy.orm import Session

from app.models.idempotency_key import (
    IdempotencyKey,
)


class IdempotencyRepository:

    @staticmethod
    def get_by_key(
        db: Session,
        key: str,
    ) -> IdempotencyKey | None:

        return (
            db.query(IdempotencyKey)
            .filter(
                IdempotencyKey.key == key
            )
            .first()
        )
    
    @staticmethod
    def create(
        db: Session,
        *,
        key: str,
        operation: str,
        resource_id,
        request_hash: str,
        response_status: int,
        response_body: dict,
    ) -> IdempotencyKey:

        record = IdempotencyKey(
            key=key,
            operation=operation,
            resource_id=resource_id,
            request_hash=request_hash,
            response_status=response_status,
            response_body=response_body,
        )

        db.add(record)

        return record