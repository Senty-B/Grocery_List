"""drop household.invite_code column

Invite-code self-join was removed when account creation moved behind the
admin area, so the column no longer carries any meaning.

Revision ID: 20260423_0004
Revises: 20260423_0003
Create Date: 2026-04-23 13:30:00

"""

from alembic import op
import sqlalchemy as sa


revision = "20260423_0004"
down_revision = "20260423_0003"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("household") as batch_op:
        batch_op.drop_constraint("household_invite_code_key", type_="unique")
        batch_op.drop_column("invite_code")


def downgrade():
    with op.batch_alter_table("household") as batch_op:
        batch_op.add_column(
            sa.Column(
                "invite_code",
                sa.String(length=32),
                nullable=False,
                server_default=sa.text("''"),
            )
        )
        batch_op.create_unique_constraint(
            "household_invite_code_key",
            ["invite_code"],
        )
