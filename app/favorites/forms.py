from flask_wtf import FlaskForm
from wtforms import IntegerField, StringField, SubmitField
from wtforms.validators import DataRequired, NumberRange, Optional


class AddFavoriteForm(FlaskForm):
    name = StringField("Item Name", validators=[DataRequired()])
    quantity = IntegerField(
        "Default Quantity",
        default=1,
        validators=[Optional(), NumberRange(min=1, max=9999)],
    )
    unit = StringField("Default Unit", validators=[Optional()])
    note = StringField("Default Note", validators=[Optional()])
    submit = SubmitField("Add to Favorites")
