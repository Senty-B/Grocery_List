"""initial tables

Revision ID: 20260406_0001
Revises:
Create Date: 2026-04-06 14:48:00

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260406_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "household",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("invite_code", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invite_code"),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("household_id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "role",
            sa.String(length=20),
            server_default=sa.text("'member'"),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["household_id"],
            ["household.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )
    op.create_index("ix_users_household_id", "users", ["household_id"], unique=False)

    op.create_table(
        "favorite_item",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("household_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("normalized_name", sa.String(length=100), nullable=False),
        sa.Column(
            "default_quantity_value",
            sa.Numeric(precision=10, scale=2),
            server_default=sa.text("1.00"),
            nullable=False,
        ),
        sa.Column("default_unit", sa.String(length=20), nullable=True),
        sa.Column("default_note", sa.String(length=255), nullable=True),
        sa.Column(
            "sort_order",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["household_id"],
            ["household.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_favorite_household_normalized",
        "favorite_item",
        ["household_id", "normalized_name"],
        unique=False,
    )
    op.create_index(
        "ix_favorite_household_sort",
        "favorite_item",
        ["household_id", "sort_order"],
        unique=False,
    )

    op.create_table(
        "grocery_item",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("household_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("normalized_name", sa.String(length=100), nullable=False),
        sa.Column(
            "normalized_unit",
            sa.String(length=20),
            server_default=sa.text("''"),
            nullable=False,
        ),
        sa.Column(
            "normalized_note",
            sa.String(length=255),
            server_default=sa.text("''"),
            nullable=False,
        ),
        sa.Column(
            "quantity_value",
            sa.Numeric(precision=10, scale=2),
            server_default=sa.text("1.00"),
            nullable=False,
        ),
        sa.Column("unit", sa.String(length=20), nullable=True),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default=sa.text("'active'"),
            nullable=False,
        ),
        sa.Column("checked_by_user_id", sa.Integer(), nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["checked_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["household_id"],
            ["household.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_grocery_household_normalized",
        "grocery_item",
        ["household_id", "normalized_name"],
        unique=False,
    )
    op.create_index(
        "ix_grocery_household_status",
        "grocery_item",
        ["household_id", "status"],
        unique=False,
    )
    op.create_index(
        "uq_grocery_active_dedupe",
        "grocery_item",
        ["household_id", "normalized_name", "normalized_unit", "normalized_note"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "activity_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("household_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("action_type", sa.String(length=50), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["household_id"],
            ["household.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("activity_log")
    op.drop_index("uq_grocery_active_dedupe", table_name="grocery_item")
    op.drop_index("ix_grocery_household_status", table_name="grocery_item")
    op.drop_index("ix_grocery_household_normalized", table_name="grocery_item")
    op.drop_table("grocery_item")
    op.drop_index("ix_favorite_household_sort", table_name="favorite_item")
    op.drop_index("ix_favorite_household_normalized", table_name="favorite_item")
    op.drop_table("favorite_item")
    op.drop_index("ix_users_household_id", table_name="users")
    op.drop_table("users")
    op.drop_table("household")
