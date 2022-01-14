from wtforms import Form, StringField, SubmitField
from wtforms.validators import DataRequired
from flask_appbuilder.fieldwidgets import BS3TextAreaFieldWidget, BS3TextFieldWidget
from flask_appbuilder.forms import DynamicForm


class EmailForm(DynamicForm):
    """Form for sending email to contacts."""

    subject = StringField(
        "Subject", validators=[DataRequired()], widget=BS3TextFieldWidget()
    )
    body = StringField(
        "Body", validators=[DataRequired()], widget=BS3TextAreaFieldWidget()
    )
