from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, DateField, SelectField, validators


class CreatePatientForm(FlaskForm):
    start_time = StringField("Start time", validators=[validators.DataRequired()])
    duration = StringField("Duration", validators=[validators.DataRequired()])
    first_name = StringField("First name", validators=[validators.DataRequired()])
    last_name = StringField("Last name", validators=[validators.DataRequired()])
    date_of_birth = DateField(
        "Date of birth", format="%Y-%m-%d", validators=[validators.DataRequired()]
    )
    email = StringField(
        "Email", validators=[validators.DataRequired(), validators.Email()]
    )
    phone = StringField("Phone", validators=[validators.DataRequired()])
    gender = SelectField(choices=["Male", "Female"])
    submit = SubmitField("Create")
