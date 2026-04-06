from flask_wtf import FlaskForm
from wtforms import DecimalField, StringField, SubmitField
from wtforms.validators import DataRequired, NumberRange, Optional


class AddItemForm(FlaskForm):
    name = StringField("Item Name", validators=[DataRequired()])
    quantity = DecimalField(
        "Quantity",
        default=1,
        validators=[Optional(), NumberRange(min=0.01)],
    )
    unit = StringField("Unit", validators=[Optional()])
    note = StringField("Note", validators=[Optional()])
    submit = SubmitField("Add")
