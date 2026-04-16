from datetime import date, datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


staff_subject_assignments = db.Table(
    "staff_subject_assignments",
    db.Column("user_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
    db.Column("subject_id", db.Integer, db.ForeignKey("subjects.id"), primary_key=True),
)

parent_student_links = db.Table(
    "parent_student_links",
    db.Column("parent_profile_id", db.Integer, db.ForeignKey("parent_profiles.id"), primary_key=True),
    db.Column("student_id", db.Integer, db.ForeignKey("students.id"), primary_key=True),
)


class TimestampMixin:
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class SubscriptionPlan(TimestampMixin, db.Model):
    __tablename__ = "subscription_plans"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    code = db.Column(db.String(30), unique=True, nullable=False)
    monthly_price = db.Column(db.Float, default=0, nullable=False)
    features = db.Column(db.JSON, default=list, nullable=False)

    subscriptions = db.relationship("CollegeSubscription", backref="plan", lazy=True)

    def has_feature(self, feature_key):
        return feature_key in (self.features or [])


class College(TimestampMixin, db.Model):
    __tablename__ = "colleges"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    code = db.Column(db.String(30), unique=True, nullable=False)
    subdomain = db.Column(db.String(80), unique=True, nullable=True)
    contact_email = db.Column(db.String(120), nullable=True)
    contact_phone = db.Column(db.String(30), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    subscriptions = db.relationship(
        "CollegeSubscription",
        backref="college",
        lazy=True,
        cascade="all, delete-orphan",
    )
    departments = db.relationship("Department", backref="college", lazy=True)
    users = db.relationship("User", backref="college", lazy=True)
    students = db.relationship("Student", backref="college", lazy=True)
    subjects = db.relationship("Subject", backref="college", lazy=True)
    fee_categories = db.relationship("FeeCategory", backref="college", lazy=True)
    time_slots = db.relationship("TimeSlot", backref="college", lazy=True)
    timetable_entries = db.relationship("TimetableEntry", backref="college", lazy=True)
    notifications = db.relationship("NotificationLog", backref="college", lazy=True)
    uploaded_files = db.relationship("UploadedFile", backref="college", lazy=True)

    @property
    def current_subscription(self):
        return (
            CollegeSubscription.query.filter_by(college_id=self.id)
            .order_by(CollegeSubscription.created_at.desc())
            .first()
        )

    @property
    def active_plan(self):
        subscription = self.current_subscription
        return subscription.plan if subscription and subscription.plan else None


class CollegeSubscription(TimestampMixin, db.Model):
    __tablename__ = "college_subscriptions"

    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey("colleges.id"), nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey("subscription_plans.id"), nullable=False)
    status = db.Column(db.String(30), default="active", nullable=False)
    start_date = db.Column(db.Date, default=date.today, nullable=False)
    end_date = db.Column(db.Date, nullable=True)
    razorpay_plan_id = db.Column(db.String(80), nullable=True)
    razorpay_subscription_id = db.Column(db.String(80), nullable=True)
    payment_reference = db.Column(db.String(120), nullable=True)


class Department(TimestampMixin, db.Model):
    __tablename__ = "departments"

    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey("colleges.id"), nullable=True, index=True)
    name = db.Column(db.String(120), nullable=False)
    code = db.Column(db.String(20), nullable=False)

    students = db.relationship("Student", backref="department", lazy=True)
    subjects = db.relationship("Subject", backref="department", lazy=True)

    __table_args__ = (
        db.UniqueConstraint("college_id", "name", name="uq_department_college_name"),
        db.UniqueConstraint("college_id", "code", name="uq_department_college_code"),
    )


class User(UserMixin, TimestampMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey("colleges.id"), nullable=True, index=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    full_name = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(30), nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="admin", nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=True)
    is_active_user = db.Column(db.Boolean, default=True, nullable=False)

    activities = db.relationship("ActivityLog", backref="actor", lazy=True)
    department = db.relationship("Department", backref="team_members", lazy=True)
    assigned_subjects = db.relationship(
        "Subject",
        secondary=staff_subject_assignments,
        back_populates="assigned_staff",
        lazy="subquery",
    )
    staff_timetable = db.relationship("TimetableEntry", backref="staff_member", lazy=True)
    uploaded_items = db.relationship("UploadedFile", backref="uploaded_by", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_active(self):
        return self.is_active_user

    @property
    def display_name(self):
        return self.full_name or self.username

    @property
    def is_admin(self):
        return self.role == "admin"

    @property
    def is_staff_member(self):
        return self.role == "staff"

    @property
    def is_hod(self):
        return self.role == "hod"

    @property
    def is_student(self):
        return self.role == "student"

    @property
    def is_parent(self):
        return self.role == "parent"


class Student(TimestampMixin, db.Model):
    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey("colleges.id"), nullable=True, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=True)
    name = db.Column(db.String(120), nullable=False)
    register_no = db.Column(db.String(50), unique=True, nullable=False)
    phone = db.Column(db.String(30), nullable=True)
    year = db.Column(db.Integer, nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=False)

    portal_user = db.relationship("User", foreign_keys=[user_id], backref=db.backref("student_profile", uselist=False))
    attendance_records = db.relationship(
        "Attendance",
        backref="student",
        lazy=True,
        cascade="all, delete-orphan",
    )
    marks = db.relationship("Mark", backref="student", lazy=True, cascade="all, delete-orphan")
    summaries = db.relationship(
        "ResultSummary",
        backref="student",
        lazy=True,
        cascade="all, delete-orphan",
    )
    fee_records = db.relationship("StudentFee", backref="student", lazy=True, cascade="all, delete-orphan")
    uploaded_files = db.relationship("UploadedFile", backref="student", lazy=True)
    notifications = db.relationship("NotificationLog", backref="student", lazy=True)
    parents = db.relationship(
        "ParentProfile",
        secondary=parent_student_links,
        back_populates="students",
        lazy="subquery",
    )

    @property
    def attendance_percentage(self):
        total = len(self.attendance_records)
        if total == 0:
            return 0
        present = sum(1 for record in self.attendance_records if record.status == "Present")
        return round((present / total) * 100, 2)

    @property
    def total_fees_paid(self):
        return round(sum(record.amount_paid for record in self.fee_records), 2)

    @property
    def total_fees_due(self):
        return round(sum(max(record.total_amount - record.amount_paid, 0) for record in self.fee_records), 2)


class ParentProfile(TimestampMixin, db.Model):
    __tablename__ = "parent_profiles"

    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey("colleges.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    relationship = db.Column(db.String(50), default="Parent", nullable=False)

    college = db.relationship("College", backref="parent_profiles", lazy=True)
    user = db.relationship("User", backref=db.backref("parent_profile", uselist=False), lazy=True)
    students = db.relationship(
        "Student",
        secondary=parent_student_links,
        back_populates="parents",
        lazy="subquery",
    )


class Attendance(TimestampMixin, db.Model):
    __tablename__ = "attendance"

    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey("colleges.id"), nullable=True, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    attendance_date = db.Column(db.Date, default=date.today, nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False)

    __table_args__ = (
        db.UniqueConstraint("student_id", "attendance_date", name="uq_attendance_student_date"),
    )


class Subject(TimestampMixin, db.Model):
    __tablename__ = "subjects"

    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey("colleges.id"), nullable=True, index=True)
    name = db.Column(db.String(120), nullable=False)
    code = db.Column(db.String(30), unique=True, nullable=False)
    max_marks = db.Column(db.Integer, default=100, nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=True)

    marks = db.relationship("Mark", backref="subject", lazy=True)
    assigned_staff = db.relationship(
        "User",
        secondary=staff_subject_assignments,
        back_populates="assigned_subjects",
        lazy="subquery",
    )
    timetable_entries = db.relationship("TimetableEntry", backref="subject", lazy=True)


class Mark(TimestampMixin, db.Model):
    __tablename__ = "marks"

    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey("colleges.id"), nullable=True, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"), nullable=False)
    exam_type = db.Column(db.String(30), default="Internal", nullable=False)
    marks_obtained = db.Column(db.Float, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("student_id", "subject_id", "exam_type", name="uq_mark_student_subject_exam"),
    )


class ResultSummary(TimestampMixin, db.Model):
    __tablename__ = "results_summary"

    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey("colleges.id"), nullable=True, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    result_type = db.Column(db.String(30), nullable=False)
    exam_name = db.Column(db.String(120), nullable=False)
    semester = db.Column(db.String(30), nullable=True)
    total_marks = db.Column(db.Float, nullable=False)
    percentage = db.Column(db.Float, nullable=False)
    result_status = db.Column(db.String(30), default="Pass", nullable=False)


class FeeCategory(TimestampMixin, db.Model):
    __tablename__ = "fee_categories"

    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey("colleges.id"), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    default_amount = db.Column(db.Float, default=0, nullable=False)

    fees = db.relationship("StudentFee", backref="category", lazy=True)

    __table_args__ = (
        db.UniqueConstraint("college_id", "name", name="uq_fee_category_name"),
    )


class StudentFee(TimestampMixin, db.Model):
    __tablename__ = "student_fees"

    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey("colleges.id"), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    fee_category_id = db.Column(db.Integer, db.ForeignKey("fee_categories.id"), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    amount_paid = db.Column(db.Float, default=0, nullable=False)
    due_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), default="pending", nullable=False)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    payments = db.relationship("FeePayment", backref="student_fee", lazy=True, cascade="all, delete-orphan")
    created_by = db.relationship("User", foreign_keys=[created_by_user_id], lazy=True)

    @property
    def due_amount(self):
        return round(max(self.total_amount - self.amount_paid, 0), 2)


class FeePayment(TimestampMixin, db.Model):
    __tablename__ = "fee_payments"

    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey("colleges.id"), nullable=False, index=True)
    student_fee_id = db.Column(db.Integer, db.ForeignKey("student_fees.id"), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_date = db.Column(db.Date, default=date.today, nullable=False)
    payment_method = db.Column(db.String(50), default="cash", nullable=False)
    reference = db.Column(db.String(120), nullable=True)


class TimeSlot(TimestampMixin, db.Model):
    __tablename__ = "time_slots"

    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey("colleges.id"), nullable=False, index=True)
    label = db.Column(db.String(80), nullable=False)
    weekday = db.Column(db.String(20), nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)

    entries = db.relationship("TimetableEntry", backref="time_slot", lazy=True)


class TimetableEntry(TimestampMixin, db.Model):
    __tablename__ = "timetable_entries"

    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey("colleges.id"), nullable=False, index=True)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"), nullable=False)
    staff_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    time_slot_id = db.Column(db.Integer, db.ForeignKey("time_slots.id"), nullable=False)
    room = db.Column(db.String(50), nullable=False)

    department = db.relationship("Department", backref="timetable_entries", lazy=True)


class NotificationLog(TimestampMixin, db.Model):
    __tablename__ = "notification_logs"

    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey("colleges.id"), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=True)
    triggered_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    channel = db.Column(db.String(30), nullable=False)
    recipient = db.Column(db.String(120), nullable=False)
    message = db.Column(db.Text, nullable=False)
    trigger_type = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(30), default="queued", nullable=False)
    provider = db.Column(db.String(50), nullable=True)
    external_reference = db.Column(db.String(120), nullable=True)

    triggered_by = db.relationship("User", foreign_keys=[triggered_by_user_id], lazy=True)


class UploadedFile(TimestampMixin, db.Model):
    __tablename__ = "uploaded_files"

    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey("colleges.id"), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=True)
    uploaded_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    category = db.Column(db.String(50), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)
    content_type = db.Column(db.String(120), nullable=True)
    description = db.Column(db.String(255), nullable=True)


class Setting(TimestampMixin, db.Model):
    __tablename__ = "settings"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(80), unique=True, nullable=False)
    value = db.Column(db.String(255), nullable=False)


class ActivityLog(TimestampMixin, db.Model):
    __tablename__ = "activity_logs"

    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey("colleges.id"), nullable=True, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    action = db.Column(db.String(255), nullable=False)
    module = db.Column(db.String(50), nullable=False)
