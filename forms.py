from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import (
    DecimalField,
    IntegerField,
    PasswordField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Email, EqualTo, InputRequired, Length, NumberRange, Optional


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(max=64)])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")


class RegisterForm(LoginForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8, max=128)])
    confirm_password = PasswordField("Confirm password", validators=[DataRequired(), EqualTo("password")])
    submit = SubmitField("Create account")


class ItemForm(FlaskForm):
    name = StringField("Product name", validators=[DataRequired(), Length(max=120)])
    description = TextAreaField("Description", validators=[Optional(), Length(max=500)])
    quantity = IntegerField(
        "Quantity", default=0, validators=[InputRequired(), NumberRange(min=0, max=1_000_000)]
    )
    price = DecimalField(
        "Unit price", default=0, validators=[InputRequired(), NumberRange(min=0, max=1_000_000)]
    )
    category = StringField("Category", validators=[Optional(), Length(max=80)])
    supplier_id = SelectField("Supplier", coerce=int, choices=[])
    image = FileField("Product image", validators=[FileAllowed(["jpg", "jpeg", "png", "gif"])])
    submit = SubmitField("Save product")


class MovementForm(FlaskForm):
    kind = SelectField(
        "Movement type", choices=[("receipt", "Stock received"), ("consumption", "Stock consumed")]
    )
    quantity = IntegerField("Units", validators=[InputRequired(), NumberRange(min=1, max=1_000_000)])
    note = StringField("Note", validators=[Optional(), Length(max=300)])
    submit = SubmitField("Record movement")


class SupplierForm(FlaskForm):
    name = StringField("Supplier name", validators=[DataRequired(), Length(max=120)])
    email = StringField("Contact email", validators=[Optional(), Email(), Length(max=120)])
    submit = SubmitField("Add supplier")


class ProfileForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField("Email", validators=[Optional(), Email(), Length(max=120)])
    bio = TextAreaField("Bio", validators=[Optional(), Length(max=300)])
    submit = SubmitField("Save profile")


class PasswordForm(FlaskForm):
    current_password = PasswordField("Current password", validators=[DataRequired()])
    new_password = PasswordField("New password", validators=[DataRequired(), Length(min=8, max=128)])
    confirm_password = PasswordField("Confirm password", validators=[DataRequired(), EqualTo("new_password")])
    submit = SubmitField("Change password")
