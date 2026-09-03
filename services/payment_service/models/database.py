import time
import os

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://admin:password123@postgres-payment:5432/db_payment",
)

Base = declarative_base()
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def initialize_database():
    for attempt in range(30):
        try:
            inspector = inspect(engine)
            board_columns = {
                column["name"] for column in inspector.get_columns("payment_boards")
            } if inspector.has_table("payment_boards") else set()
            needs_recreate = board_columns and (
                "code" not in board_columns
                or "customer_id" not in board_columns
                or "total_amount" not in board_columns
            )
            if needs_recreate:
                with engine.begin() as connection:
                    has_rows = connection.execute(
                        text("SELECT EXISTS (SELECT 1 FROM payment_boards)")
                    ).scalar()
                    if has_rows:
                        raise RuntimeError(
                            "Không thể đổi schema payment khi database đã có dữ liệu"
                        )
                    connection.execute(text(
                        "DROP TABLE IF EXISTS payment_idempotency_key, "
                        "payment_outbox_event, payment_workflow_steps, "
                        "payment_workflow_instances, payment_status_histories, "
                        "payment_details, payment_boards CASCADE"
                    ))
            with engine.begin() as connection:
                existing_columns = {
                    column["name"] for column in inspect(engine).get_columns("payment_boards")
                } if inspect(engine).has_table("payment_boards") else set()
                detail_columns = {
                    column["name"] for column in inspect(engine).get_columns("payment_details")
                } if inspect(engine).has_table("payment_details") else set()
                if "operation_date" not in detail_columns and inspect(engine).has_table("payment_details"):
                    connection.execute(text("ALTER TABLE payment_details ADD COLUMN operation_date DATE"))
                migrations = {
                    "payment_type": "ALTER TABLE payment_boards ADD COLUMN payment_type VARCHAR(30) NOT NULL DEFAULT 'STANDARD'",
                    "parent_payment_id": "ALTER TABLE payment_boards ADD COLUMN parent_payment_id VARCHAR(36) REFERENCES payment_boards(id) ON DELETE SET NULL",
                    "adjustment_reason": "ALTER TABLE payment_boards ADD COLUMN adjustment_reason TEXT",
                    "price_list_id": "ALTER TABLE payment_boards ADD COLUMN price_list_id VARCHAR(36)",
                    "price_list_version_id": "ALTER TABLE payment_boards ADD COLUMN price_list_version_id VARCHAR(36)",
                    "price_list_version_number": "ALTER TABLE payment_boards ADD COLUMN price_list_version_number VARCHAR(50)",
                }
                for column, statement in migrations.items():
                    if column not in existing_columns:
                        connection.execute(text(statement))
                if "note" in existing_columns:
                    connection.execute(text("ALTER TABLE payment_boards DROP COLUMN note"))
                connection.execute(text(
                    "CREATE INDEX IF NOT EXISTS ix_payment_boards_parent_payment_id "
                    "ON payment_boards(parent_payment_id)"
                ))
                connection.execute(text(
                    "CREATE INDEX IF NOT EXISTS ix_payment_boards_parent_status "
                    "ON payment_boards(parent_payment_id, status)"
                ))
            Base.metadata.create_all(bind=engine)
            return
        except Exception:
            if attempt == 29:
                raise
            time.sleep(2)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
