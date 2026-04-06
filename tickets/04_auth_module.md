# Ticket 4: Auth Module — Registration, Login & Household Creation

**Phase:** 2 — Core Backend  
**Priority:** Critical  
**Dependencies:** Ticket 2, Ticket 3  
**Estimated effort:** Medium

---

## Why This Matters

Users must be able to create an account, create a household, log in, log out, and join an existing household via invite code. This is the entry point of the entire app — nothing works without authentication.

## Reference

- Routes: `Route_Contract.md` sections 3, 4
- Schema: `Schema_API_UI_sub_specs.md` sections 1.1, 1.2, 2.1

---

## Tasks

### 1. Create WTForms form classes

`app/auth/forms.py`:

```python
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo


class RegistrationForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=3, max=50)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField(
        "Confirm Password", validators=[DataRequired(), EqualTo("password")]
    )
    household_name = StringField("Household Name", validators=[DataRequired(), Length(max=100)])
    submit = SubmitField("Create Account")


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Log In")


class JoinHouseholdForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=3, max=50)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField(
        "Confirm Password", validators=[DataRequired(), EqualTo("password")]
    )
    invite_code = StringField("Invite Code", validators=[DataRequired(), Length(max=32)])
    submit = SubmitField("Join Household")
```

**What is WTForms?** It's a library that handles form validation on the server side. Each `Field` has `validators` that check the data. `FlaskForm` automatically includes CSRF protection.

### 2. Create the auth service layer

`app/auth/services.py`:

```python
import bcrypt
import logging
from app.extensions import db
from app.models.user import User
from app.models.household import Household
from app.common.utils import generate_invite_code, log_activity
from app.common.validators import validate_username, validate_password

logger = logging.getLogger(__name__)


def hash_password(plain_password):
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def check_password(plain_password, hashed):
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed.encode("utf-8"))


def register_owner(username, password, household_name):
    """Create a new household and register the owner user.
    Returns the created User."""
    validate_username(username)
    validate_password(password)

    if User.query.filter_by(username=username).first():
        raise ValueError("Username is already taken.")

    household = Household(
        name=household_name.strip(),
        invite_code=generate_invite_code(),
    )
    db.session.add(household)
    db.session.flush()  # get household.id before creating user

    user = User(
        household_id=household.id,
        username=username.strip(),
        password_hash=hash_password(password),
        role="owner",
    )
    db.session.add(user)
    db.session.commit()

    logger.info("Registered owner '%s' for household '%s'", username, household_name)
    return user


def join_household(username, password, invite_code):
    """Register a new user and add them to an existing household via invite code.
    Returns the created User."""
    validate_username(username)
    validate_password(password)

    household = Household.query.filter_by(invite_code=invite_code.strip().upper()).first()
    if not household:
        raise ValueError("Invalid invite code.")

    active_member_count = User.query.filter_by(
        household_id=household.id, is_active=True
    ).count()
    if active_member_count >= 5:
        raise ValueError("This household has reached the maximum of 5 members.")

    if User.query.filter_by(username=username).first():
        raise ValueError("Username is already taken.")

    user = User(
        household_id=household.id,
        username=username.strip(),
        password_hash=hash_password(password),
        role="member",
    )
    db.session.add(user)
    db.session.commit()

    logger.info("User '%s' joined household '%s'", username, household.name)
    return user


def authenticate_user(username, password):
    """Verify credentials. Returns User if valid, None otherwise."""
    user = User.query.filter_by(username=username, is_active=True).first()
    if user and check_password(password, user.password_hash):
        return user
    return None
```

### 3. Create the auth routes

`app/auth/routes.py`:

```python
import logging
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.auth.forms import RegistrationForm, LoginForm, JoinHouseholdForm
from app.auth.services import register_owner, join_household, authenticate_user

logger = logging.getLogger(__name__)
auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("grocery.index"))

    form = LoginForm()
    if form.validate_on_submit():
        user = authenticate_user(form.username.data, form.password.data)
        if user:
            login_user(user)
            logger.info("User '%s' logged in", user.username)
            next_page = request.args.get("next")
            return redirect(next_page or url_for("grocery.index"))
        flash("Invalid username or password.", "error")
    return render_template("auth/login.html", form=form)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("grocery.index"))

    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            user = register_owner(
                form.username.data,
                form.password.data,
                form.household_name.data,
            )
            login_user(user)
            flash("Account created! Welcome to your household.", "success")
            return redirect(url_for("grocery.index"))
        except ValueError as e:
            flash(str(e), "error")
    return render_template("auth/register.html", form=form)


@auth_bp.route("/register/join", methods=["GET", "POST"])
def register_join():
    if current_user.is_authenticated:
        return redirect(url_for("grocery.index"))

    form = JoinHouseholdForm()
    if form.validate_on_submit():
        try:
            user = join_household(
                form.username.data,
                form.password.data,
                form.invite_code.data,
            )
            login_user(user)
            flash("You've joined the household!", "success")
            return redirect(url_for("grocery.index"))
        except ValueError as e:
            flash(str(e), "error")
    return render_template("auth/join.html", form=form)


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logger.info("User '%s' logged out", current_user.username)
    logout_user()
    return redirect(url_for("auth.login"))
```

### 4. Create placeholder templates

Create minimal templates so routes don't crash. Full styling is in Ticket 9/10.

- `app/templates/auth/login.html`
- `app/templates/auth/register.html`
- `app/templates/auth/join.html`

Each should extend a base template and render the form fields with CSRF token. Example for login:

```html
{% extends "base.html" %}
{% block content %}
<h1>Login</h1>
<form method="POST">
  {{ form.hidden_tag() }}
  <div>{{ form.username.label }} {{ form.username() }}</div>
  <div>{{ form.password.label }} {{ form.password() }}</div>
  <button type="submit">Log In</button>
</form>
<p>New household? <a href="{{ url_for('auth.register') }}">Register</a></p>
<p>Have an invite code? <a href="{{ url_for('auth.register_join') }}">Join</a></p>
{% endblock %}
```

Create a minimal `app/templates/base.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{% block title %}Grocery List{% endblock %}</title>
</head>
<body>
  {% with messages = get_flashed_messages(with_categories=true) %}
    {% for category, message in messages %}
      <p class="{{ category }}">{{ message }}</p>
    {% endfor %}
  {% endwith %}
  {% block content %}{% endblock %}
</body>
</html>
```

---

## Acceptance Criteria

- [ ] A new user can register and a household is automatically created
- [ ] The registered user is the household `owner`
- [ ] An invite code is generated and stored on the household
- [ ] A second user can join using the invite code
- [ ] The 6th user trying to join a household gets a "maximum members" error
- [ ] Login with correct credentials redirects to `/grocery`
- [ ] Login with wrong credentials shows an error message
- [ ] Passwords are stored as bcrypt hashes (never plaintext)
- [ ] `POST /logout` ends the session and redirects to `/login`
- [ ] CSRF token is present and validated on all POST forms
- [ ] Username uniqueness is enforced (duplicate usernames rejected)
