"""add approval round

Revision ID: bd59ea8f3508
Revises: 705cdf52bc0e
Create Date: 2026-09-03 11:48:19.501752

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bd59ea8f3508'
down_revision: Union[str, None] = '705cdf52bc0e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "contract_approvals",
        sa.Column(
            "approval_round",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
    )

    op.create_index(
        "ix_contract_approvals_approval_round",
        "contract_approvals",
        ["approval_round"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_contract_approvals_approval_round",
        table_name="contract_approvals",
    )

    op.drop_column(
        "contract_approvals",
        "approval_round",
    )
