from datetime import datetime, timezone

from app.extensions import db


class Household(db.Model):
    __tablename__ = "household"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    invite_code = db.Column(db.String(32), nullable=False, unique=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    users = db.relationship(
        "User",
        back_populates="household",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    grocery_items = db.relationship(
        "GroceryItem",
        back_populates="household",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    favorite_items = db.relationship(
        "FavoriteItem",
        back_populates="household",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    activity_logs = db.relationship(
        "ActivityLog",
        back_populates="household",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
