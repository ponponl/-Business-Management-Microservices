"""create contract approvals table

Revision ID: 705cdf52bc0e
Revises: 3113787cb848
Create Date: 2026-09-02 07:02:34.220526

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '705cdf52bc0e'
down_revision: Union[str, None] = '3113787cb848'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "contract_approvals",
        sa.Column(
            "approval_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "contract_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "step_no",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "approver_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=30),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column(
            "comment",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["contract_id"],
            ["contracts.contract_id"],
        ),
        sa.PrimaryKeyConstraint(
            "approval_id",
        ),
    )

    op.create_index(
        "ix_contract_approvals_contract_id",
        "contract_approvals",
        ["contract_id"],
        unique=False,
    )

    op.create_index(
        "ix_contract_approvals_approver_id",
        "contract_approvals",
        ["approver_id"],
        unique=False,
    )

    op.create_index(
        "ix_contract_approvals_status",
        "contract_approvals",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_contract_approvals_status",
        table_name="contract_approvals",
    )

    op.drop_index(
        "ix_contract_approvals_approver_id",
        table_name="contract_approvals",
    )

    op.drop_index(
        "ix_contract_approvals_contract_id",
        table_name="contract_approvals",
    )

    op.drop_table(
        "contract_approvals",
    )
