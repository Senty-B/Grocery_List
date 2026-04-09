from flask_wtf import FlaskForm
from wtforms import DecimalField, StringField, SubmitField
from wtforms.validators import DataRequired, NumberRange, Optional


class AddFavoriteForm(FlaskForm):
    name = StringField("Item Name", validators=[DataRequired()])
    quantity = DecimalField(
        "Default Quantity",
        default=1,
        validators=[Optional(), NumberRange(min=0.01)],
    )
    unit = StringField("Default Unit", validators=[Optional()])
    note = StringField("Default Note", validators=[Optional()])
    submit = SubmitField("Add to Favorites")
