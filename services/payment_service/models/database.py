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
            history_columns = {
                column["name"] for column in inspector.get_columns("payment_status_histories")
            } if inspector.has_table("payment_status_histories") else set()
            needs_recreate = board_columns and (
                "code" not in board_columns
                or "customer_id" not in board_columns
                or "total_amount" not in board_columns
                or "action" not in history_columns
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
