# Ticket 7: Household Module — Invite Codes & Member Management

**Phase:** 2 — Core Backend  
**Priority:** High  
**Dependencies:** Ticket 4  
**Estimated effort:** Small

---

## Why This Matters

The household owner needs to see their invite code to share it, rotate it if needed, and view who is in the household.

## Reference

- Routes: `Route_Contract.md` section 4

---

## Tasks

### 1. Create the household service layer

`app/household/services.py`:

```python
import logging
from app.extensions import db
from app.models.household import Household
from app.models.user import User
from app.common.utils import generate_invite_code

logger = logging.getLogger(__name__)


def get_household_info(household_id):
    """Return the household and its members."""
    household = db.session.get(Household, household_id)
    if not household:
        raise ValueError("Household not found.")
    members = User.query.filter_by(household_id=household_id, is_active=True).all()
    return household, members


def rotate_invite_code(household_id):
    """Generate a new invite code for the household."""
    household = db.session.get(Household, household_id)
    if not household:
        raise ValueError("Household not found.")
    household.invite_code = generate_invite_code()
    db.session.commit()
    logger.info("Invite code rotated for household %s", household_id)
    return household.invite_code
```

### 2. Create the household routes

`app/household/routes.py`:

```python
import logging
from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from app.common.authz import require_household, require_owner
from app.household.services import get_household_info, rotate_invite_code

logger = logging.getLogger(__name__)
household_bp = Blueprint("household", __name__)


@household_bp.route("/")
@login_required
@require_household
def index():
    household, members = get_household_info(current_user.household_id)
    return render_template(
        "household/index.html",
        household=household,
        members=members,
        is_owner=current_user.role == "owner",
    )


@household_bp.route("/rotate-code", methods=["POST"])
@login_required
@require_owner
def rotate_code():
    new_code = rotate_invite_code(current_user.household_id)
    flash(f"New invite code: {new_code}", "success")
    return redirect(url_for("household.index"))
```

### 3. Create placeholder template

`app/templates/household/index.html` — shows household name, invite code (if owner), member list.

---

## Acceptance Criteria

- [ ] Owner can view the household page with invite code visible
- [ ] Members can view the household page but cannot see invite code (or it's view-only)
- [ ] Owner can rotate the invite code, and old code stops working
- [ ] Member list shows all active members with their roles
- [ ] `@require_owner` blocks members from accessing `/household/rotate-code`
