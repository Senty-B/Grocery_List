from datetime import datetime, timezone

from flask_login import UserMixin

from app.extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    is_admin = False

    id = db.Column(db.Integer, primary_key=True)
    household_id = db.Column(
        db.Integer,
        db.ForeignKey("household.id", ondelete="CASCADE"),
        nullable=False,
    )
    username = db.Column(db.String(50), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="member")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    failed_login_count = db.Column(db.Integer, nullable=False, default=0)
    locked_until = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    household = db.relationship("Household", back_populates="users")
    created_grocery_items = db.relationship(
        "GroceryItem",
        foreign_keys="GroceryItem.created_by_user_id",
        back_populates="created_by_user",
        lazy="dynamic",
    )
    checked_grocery_items = db.relationship(
        "GroceryItem",
        foreign_keys="GroceryItem.checked_by_user_id",
        back_populates="checked_by_user",
        lazy="dynamic",
    )
    activity_logs = db.relationship(
        "ActivityLog",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
