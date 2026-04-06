from datetime import datetime, timezone

from app.extensions import db


class FavoriteItem(db.Model):
    __tablename__ = "favorite_item"

    id = db.Column(db.Integer, primary_key=True)
    household_id = db.Column(
        db.Integer,
        db.ForeignKey("household.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = db.Column(db.String(100), nullable=False)
    normalized_name = db.Column(db.String(100), nullable=False)
    default_quantity_value = db.Column(db.Numeric(10, 2), nullable=False, default=1.00)
    default_unit = db.Column(db.String(20), nullable=True)
    default_note = db.Column(db.String(255), nullable=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
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
        db.Index("ix_favorite_household_sort", "household_id", "sort_order"),
        db.Index("ix_favorite_household_normalized", "household_id", "normalized_name"),
    )

    household = db.relationship("Household", back_populates="favorite_items")
