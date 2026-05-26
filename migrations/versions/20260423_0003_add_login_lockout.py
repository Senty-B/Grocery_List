"""add login lockout tracking columns

Revision ID: 20260423_0003
Revises: 20260423_0002
Create Date: 2026-04-23 13:00:00

"""

from alembic import op
import sqlalchemy as sa


revision = "20260423_0003"
down_revision = "20260423_0002"
branch_labels = None
depends_on = None


def upgrade():
    for table in ("users", "admin_user"):
        op.add_column(
            table,
            sa.Column(
                "failed_login_count",
                sa.Integer(),
                server_default=sa.text("0"),
                nullable=False,
            ),
        )
        op.add_column(
            table,
            sa.Column(
                "locked_until",
                sa.DateTime(timezone=True),
                nullable=True,
            ),
        )


def downgrade():
    for table in ("users", "admin_user"):
        op.drop_column(table, "locked_until")
        op.drop_column(table, "failed_login_count")
