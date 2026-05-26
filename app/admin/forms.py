from flask_wtf import FlaskForm
from wtforms import (
    PasswordField,
    SelectField,
    StringField,
    SubmitField,
)
from wtforms.validators import DataRequired, EqualTo, Length


class AdminLoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Log In")


class CreateHouseholdForm(FlaskForm):
    household_name = StringField(
        "Household Name",
        validators=[DataRequired(), Length(max=100)],
    )
    owner_username = StringField(
        "Owner Username",
        validators=[DataRequired(), Length(min=3, max=50)],
    )
    owner_password = PasswordField(
        "Owner Password",
        validators=[DataRequired(), Length(min=8)],
    )
    owner_confirm_password = PasswordField(
        "Confirm Password",
        validators=[DataRequired(), EqualTo("owner_password")],
    )
    submit = SubmitField("Create Household")


class CreateUserForm(FlaskForm):
    """Admin-driven user creation. Household list is populated at runtime."""

    household_id = SelectField(
        "Household",
        coerce=int,
        validators=[DataRequired()],
    )
    role = SelectField(
        "Role",
        choices=[("member", "Member"), ("owner", "Owner")],
        validators=[DataRequired()],
    )
    username = StringField(
        "Username",
        validators=[DataRequired(), Length(min=3, max=50)],
    )
    password = PasswordField(
        "Password",
        validators=[DataRequired(), Length(min=8)],
    )
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[DataRequired(), EqualTo("password")],
    )
    submit = SubmitField("Create User")
