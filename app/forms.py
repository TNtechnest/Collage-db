from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired
from wtforms import (
    DateField,
    FloatField,
    PasswordField,
    SelectField,
    SelectMultipleField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.fields import IntegerField
from wtforms.fields.datetime import TimeField
from wtforms.validators import DataRequired, Email, Length, NumberRange, Optional


class LoginForm(FlaskForm):
    username = StringField("Username or Email", validators=[DataRequired(), Length(min=3, max=120)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6, max=64)])
    submit = SubmitField("Sign In")


class StudentForm(FlaskForm):
    name = StringField("Student Name", validators=[DataRequired(), Length(max=120)])
    register_no = StringField("Register Number", validators=[DataRequired(), Length(max=50)])
    phone = StringField("Student Phone", validators=[Optional(), Length(max=30)])
    department_id = SelectField("Department", coerce=int, validators=[DataRequired()])
    year = SelectField(
        "Year",
        coerce=int,
        choices=[(1, "1st Year"), (2, "2nd Year"), (3, "3rd Year"), (4, "4th Year")],
        validators=[DataRequired()],
    )
    parent_name = StringField("Parent Name", validators=[Optional(), Length(max=120)])
    parent_phone = StringField("Parent Phone", validators=[Optional(), Length(max=30)])
    parent_email = StringField("Parent Email", validators=[Optional(), Email(), Length(max=120)])
    submit = SubmitField("Save Student")


class AttendanceForm(FlaskForm):
    attendance_date = DateField("Attendance Date", validators=[DataRequired()])
    department_id = SelectField("Department", coerce=int, validators=[DataRequired()])
    submit = SubmitField("Load Students")


class InternalMarkForm(FlaskForm):
    student_id = SelectField("Student", coerce=int, validators=[DataRequired()])
    subject_id = SelectField("Subject", coerce=int, validators=[DataRequired()])
    exam_type = SelectField(
        "Exam Type",
        choices=[("Internal", "Internal"), ("Model", "Model")],
        validators=[DataRequired()],
    )
    marks_obtained = FloatField("Marks Obtained", validators=[DataRequired(), NumberRange(min=0, max=100)])
    submit = SubmitField("Save Marks")


class UniversityUploadForm(FlaskForm):
    exam_name = StringField("Exam Name", validators=[DataRequired(), Length(max=120)])
    semester = StringField("Semester", validators=[DataRequired(), Length(max=30)])
    excel_file = FileField(
        "Excel File",
        validators=[FileRequired(), FileAllowed(["xlsx"], "Only .xlsx files are supported")],
    )
    submit = SubmitField("Upload Results")


class ReportFilterForm(FlaskForm):
    department_id = SelectField("Department", coerce=int, validate_choice=False)
    start_date = DateField("Start Date", validators=[DataRequired()])
    end_date = DateField("End Date", validators=[DataRequired()])
    submit = SubmitField("Apply Filters")


class SettingsForm(FlaskForm):
    college_name = StringField("College Name", validators=[DataRequired(), Length(max=150)])
    college_code = StringField("College Code", validators=[DataRequired(), Length(max=30)])
    contact_email = StringField("Contact Email", validators=[Optional(), Email(), Length(max=120)])
    contact_phone = StringField("Contact Phone", validators=[Optional(), Length(max=30)])
    submit = SubmitField("Save Settings")


class DepartmentForm(FlaskForm):
    name = StringField("Department Name", validators=[DataRequired(), Length(max=120)])
    code = StringField("Department Code", validators=[DataRequired(), Length(max=20)])
    submit = SubmitField("Add Department")


class SubjectForm(FlaskForm):
    name = StringField("Subject Name", validators=[DataRequired(), Length(max=120)])
    code = StringField("Subject Code", validators=[DataRequired(), Length(max=30)])
    department_id = SelectField("Department", coerce=int, validators=[DataRequired()])
    max_marks = IntegerField("Maximum Marks", validators=[DataRequired(), NumberRange(min=1, max=500)])
    submit = SubmitField("Save Subject")


class StaffForm(FlaskForm):
    full_name = StringField("Name", validators=[DataRequired(), Length(max=120)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    phone = StringField("Phone", validators=[Optional(), Length(max=30)])
    department_id = SelectField("Department", coerce=int, validate_choice=False)
    role = SelectField(
        "Role",
        choices=[("staff", "Staff"), ("hod", "HOD"), ("admin", "Admin")],
        validators=[DataRequired()],
    )
    password = PasswordField("Password", validators=[Optional(), Length(min=6, max=64)])
    subject_ids = SelectMultipleField("Assigned Subjects", coerce=int, validate_choice=False)
    submit = SubmitField("Save Staff")


class FeeCategoryForm(FlaskForm):
    name = StringField("Fee Category", validators=[DataRequired(), Length(max=100)])
    description = StringField("Description", validators=[Optional(), Length(max=255)])
    default_amount = FloatField("Default Amount", validators=[DataRequired(), NumberRange(min=0)])
    submit = SubmitField("Save Category")


class StudentFeeForm(FlaskForm):
    student_id = SelectField("Student", coerce=int, validators=[DataRequired()])
    fee_category_id = SelectField("Fee Category", coerce=int, validators=[DataRequired()])
    total_amount = FloatField("Total Amount", validators=[DataRequired(), NumberRange(min=0)])
    due_date = DateField("Due Date", validators=[Optional()])
    submit = SubmitField("Assign Fee")


class FeePaymentForm(FlaskForm):
    amount = FloatField("Amount Received", validators=[DataRequired(), NumberRange(min=0.01)])
    payment_method = SelectField(
        "Payment Method",
        choices=[("cash", "Cash"), ("online", "Online"), ("card", "Card")],
        validators=[DataRequired()],
    )
    reference = StringField("Reference", validators=[Optional(), Length(max=120)])
    payment_date = DateField("Payment Date", validators=[DataRequired()])
    submit = SubmitField("Record Payment")


class TimeSlotForm(FlaskForm):
    label = StringField("Label", validators=[DataRequired(), Length(max=80)])
    weekday = SelectField(
        "Weekday",
        choices=[
            ("Monday", "Monday"),
            ("Tuesday", "Tuesday"),
            ("Wednesday", "Wednesday"),
            ("Thursday", "Thursday"),
            ("Friday", "Friday"),
            ("Saturday", "Saturday"),
        ],
        validators=[DataRequired()],
    )
    start_time = TimeField("Start Time", validators=[DataRequired()])
    end_time = TimeField("End Time", validators=[DataRequired()])
    submit = SubmitField("Save Slot")


class TimetableEntryForm(FlaskForm):
    department_id = SelectField("Department", coerce=int, validators=[DataRequired()])
    year = SelectField(
        "Year",
        coerce=int,
        choices=[(1, "1st Year"), (2, "2nd Year"), (3, "3rd Year"), (4, "4th Year")],
        validators=[DataRequired()],
    )
    subject_id = SelectField("Subject", coerce=int, validators=[DataRequired()])
    staff_id = SelectField("Staff", coerce=int, validators=[DataRequired()])
    time_slot_id = SelectField("Time Slot", coerce=int, validators=[DataRequired()])
    room = StringField("Room", validators=[DataRequired(), Length(max=50)])
    submit = SubmitField("Save Timetable")


class NotificationComposeForm(FlaskForm):
    student_id = SelectField("Student", coerce=int, validators=[DataRequired()])
    channel = SelectField(
        "Channel",
        choices=[("sms", "SMS"), ("whatsapp", "WhatsApp")],
        validators=[DataRequired()],
    )
    trigger_type = SelectField(
        "Trigger Type",
        choices=[("attendance", "Attendance Update"), ("results", "Result Announcement"), ("general", "General")],
        validators=[DataRequired()],
    )
    message = TextAreaField("Message", validators=[DataRequired(), Length(max=500)])
    submit = SubmitField("Send Notification")


class UploadForm(FlaskForm):
    category = SelectField(
        "Category",
        choices=[("student_document", "Student Document"), ("event_photo", "Event Photo")],
        validators=[DataRequired()],
    )
    student_id = SelectField("Student", coerce=int, validate_choice=False)
    description = StringField("Description", validators=[Optional(), Length(max=255)])
    file = FileField(
        "File",
        validators=[FileRequired(), FileAllowed(["pdf", "png", "jpg", "jpeg", "webp"], "Allowed file types: pdf, png, jpg, jpeg, webp")],
    )
    submit = SubmitField("Upload File")


class SubscriptionForm(FlaskForm):
    plan_id = SelectField("Plan", coerce=int, validators=[DataRequired()])
    status = SelectField(
        "Status",
        choices=[("active", "Active"), ("trial", "Trial"), ("expired", "Expired")],
        validators=[DataRequired()],
    )
    submit = SubmitField("Update Subscription")
