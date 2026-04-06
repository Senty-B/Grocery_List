from datetime import datetime, timezone

from app.extensions import db


class GroceryItem(db.Model):
    __tablename__ = "grocery_item"

    id = db.Column(db.Integer, primary_key=True)
    household_id = db.Column(
        db.Integer,
        db.ForeignKey("household.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = db.Column(db.String(100), nullable=False)
    normalized_name = db.Column(db.String(100), nullable=False)
    normalized_unit = db.Column(db.String(20), nullable=False, default="")
    normalized_note = db.Column(db.String(255), nullable=False, default="")
    quantity_value = db.Column(db.Numeric(10, 2), nullable=False, default=1.00)
    unit = db.Column(db.String(20), nullable=True)
    note = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="active")
    checked_by_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    checked_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_by_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        db.Index("ix_grocery_household_status", "household_id", "status"),
        db.Index("ix_grocery_household_normalized", "household_id", "normalized_name"),
    )

    household = db.relationship("Household", back_populates="grocery_items")
    created_by_user = db.relationship(
        "User",
        foreign_keys=[created_by_user_id],
        back_populates="created_grocery_items",
    )
    checked_by_user = db.relationship(
        "User",
        foreign_keys=[checked_by_user_id],
        back_populates="checked_grocery_items",
    )
