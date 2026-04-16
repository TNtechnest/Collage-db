from collections import defaultdict
from datetime import date, time, timedelta
from random import choice, randint

from app.extensions import db
from app.models import (
    Attendance,
    College,
    CollegeSubscription,
    Department,
    FeeCategory,
    FeePayment,
    Mark,
    ParentProfile,
    ResultSummary,
    Student,
    StudentFee,
    Subject,
    SubscriptionPlan,
    TimeSlot,
    TimetableEntry,
    User,
)


BASIC_FEATURES = [
    "sms_notifications",
    "fee_management",
    "student_portal",
    "parent_portal",
    "timetable",
    "document_uploads",
]

PRO_FEATURES = BASIC_FEATURES + [
    "whatsapp_notifications",
    "advanced_analytics",
    "event_gallery",
    "api_access",
    "subscription_billing",
]



def _ensure_user(email, **kwargs):
    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(email=email, username=kwargs.get("username", email))
        db.session.add(user)
    for key, value in kwargs.items():
        setattr(user, key, value)
    return user



def _student_portal_identity(register_no):
    slug = register_no.lower()
    return slug, f"student.{slug}@college.local"



def _parent_portal_identity(register_no):
    slug = register_no.lower()
    return f"parent.{slug}", f"parent.{slug}@college.local"



def seed_initial_data():
    basic_plan = SubscriptionPlan.query.filter_by(code="basic").first()
    if not basic_plan:
        basic_plan = SubscriptionPlan(name="Basic", code="basic", monthly_price=2999, features=BASIC_FEATURES)
        db.session.add(basic_plan)

    pro_plan = SubscriptionPlan.query.filter_by(code="pro").first()
    if not pro_plan:
        pro_plan = SubscriptionPlan(name="Pro", code="pro", monthly_price=7999, features=PRO_FEATURES)
        db.session.add(pro_plan)

    db.session.flush()

    college = College.query.filter_by(code="NWC").first()
    if not college:
        college = College(
            name="Northwind College",
            code="NWC",
            subdomain="northwind",
            contact_email="info@northwindcollege.edu",
            contact_phone="+91-9000000000",
        )
        db.session.add(college)
        db.session.flush()

    for user in User.query.filter(User.college_id.is_(None)).all():
        user.college_id = college.id
    for department in Department.query.filter(Department.college_id.is_(None)).all():
        department.college_id = college.id
    for student in Student.query.filter(Student.college_id.is_(None)).all():
        student.college_id = college.id
    for subject in Subject.query.filter(Subject.college_id.is_(None)).all():
        subject.college_id = college.id
    for record in Attendance.query.filter(Attendance.college_id.is_(None)).all():
        record.college_id = college.id
    for record in Mark.query.filter(Mark.college_id.is_(None)).all():
        record.college_id = college.id
    for record in ResultSummary.query.filter(ResultSummary.college_id.is_(None)).all():
        record.college_id = college.id
    for record in FeeCategory.query.filter(FeeCategory.college_id.is_(None)).all():
        record.college_id = college.id
    for record in StudentFee.query.filter(StudentFee.college_id.is_(None)).all():
        record.college_id = college.id
    for record in FeePayment.query.filter(FeePayment.college_id.is_(None)).all():
        record.college_id = college.id
    for record in TimeSlot.query.filter(TimeSlot.college_id.is_(None)).all():
        record.college_id = college.id
    for record in TimetableEntry.query.filter(TimetableEntry.college_id.is_(None)).all():
        record.college_id = college.id
    for record in ParentProfile.query.filter(ParentProfile.college_id.is_(None)).all():
        record.college_id = college.id

    if not college.current_subscription:
        db.session.add(
            CollegeSubscription(
                college_id=college.id,
                plan_id=pro_plan.id,
                status="active",
                start_date=date.today(),
                payment_reference="seed-subscription",
            )
        )

    required_departments = [
        ("Computer Science", "CSE"),
        ("Electronics", "ECE"),
        ("Business Administration", "BBA"),
    ]
    for name, code in required_departments:
        department = Department.query.filter_by(college_id=college.id, code=code).first()
        if not department:
            department = Department(name=name, code=code, college_id=college.id)
            db.session.add(department)
        else:
            department.name = name
            department.college_id = college.id
    db.session.flush()
    departments = Department.query.filter_by(college_id=college.id).all()
    department_map = {department.code: department for department in departments}

    required_subjects = [
        ("Data Structures", "CSE201", "CSE"),
        ("Database Systems", "CSE202", "CSE"),
        ("Digital Electronics", "ECE201", "ECE"),
        ("Signals and Systems", "ECE202", "ECE"),
        ("Marketing Fundamentals", "BBA201", "BBA"),
    ]
    for name, code, department_code in required_subjects:
        subject = Subject.query.filter_by(college_id=college.id, code=code).first()
        if not subject:
            subject = Subject(
                name=name,
                code=code,
                department_id=department_map[department_code].id,
                college_id=college.id,
            )
            db.session.add(subject)
        else:
            subject.name = name
            subject.department_id = department_map[department_code].id
            subject.college_id = college.id
    db.session.flush()
    subjects = Subject.query.filter_by(college_id=college.id).all()
    subject_map = {subject.code: subject for subject in subjects}

    admin = _ensure_user(
        "admin@college.local",
        username="admin",
        full_name="System Administrator",
        role="admin",
        college_id=college.id,
        department_id=None,
        phone="+91-9000000001",
    )
    if not admin.password_hash:
        admin.set_password("admin123")

    cse_staff = _ensure_user(
        "staff@college.local",
        username="staff",
        full_name="Priya Nair",
        role="staff",
        college_id=college.id,
        department_id=department_map["CSE"].id,
        phone="+91-9000000002",
    )
    if not cse_staff.password_hash:
        cse_staff.set_password("staff123")

    ece_staff = _ensure_user(
        "faculty.ece@college.local",
        username="faculty.ece@college.local",
        full_name="Arjun Verma",
        role="staff",
        college_id=college.id,
        department_id=department_map["ECE"].id,
        phone="+91-9000000003",
    )
    if not ece_staff.password_hash:
        ece_staff.set_password("faculty123")

    hod = _ensure_user(
        "hod.cse@college.local",
        username="hod.cse@college.local",
        full_name="Meera Krishnan",
        role="hod",
        college_id=college.id,
        department_id=department_map["CSE"].id,
        phone="+91-9000000004",
    )
    if not hod.password_hash:
        hod.set_password("hod12345")

    db.session.flush()

    if Student.query.filter_by(college_id=college.id).count() == 0:
        student_rows = [
            ("Aarav Menon", department_map["CSE"].id, 2, "+91-9100000001"),
            ("Diya Sharma", department_map["CSE"].id, 3, "+91-9100000002"),
            ("Kiran Patel", department_map["ECE"].id, 2, "+91-9100000003"),
            ("Nisha Rao", department_map["ECE"].id, 4, "+91-9100000004"),
            ("Rahul Iyer", department_map["BBA"].id, 1, "+91-9100000005"),
            ("Sana Joseph", department_map["BBA"].id, 3, "+91-9100000006"),
        ]
        students = []
        for index, (name, department_id, year, phone) in enumerate(student_rows, start=1):
            students.append(
                Student(
                    name=name,
                    register_no=f"REG2026{index:03d}",
                    department_id=department_id,
                    year=year,
                    phone=phone,
                    college_id=college.id,
                )
            )
        db.session.add_all(students)
        db.session.flush()
    else:
        students = Student.query.filter_by(college_id=college.id).all()
        for student in students:
            student.college_id = student.college_id or college.id

    for index, student in enumerate(students, start=1):
        if not student.phone:
            student.phone = f"+91-9100000{index:03d}"
        if not student.user_id:
            username, email = _student_portal_identity(student.register_no)
            student_user = User.query.filter_by(email=email).first()
            if not student_user:
                student_user = User(
                    username=username,
                    email=email,
                    full_name=student.name,
                    role="student",
                    college_id=college.id,
                    department_id=student.department_id,
                    phone=student.phone,
                )
                student_user.set_password(student.register_no.lower())
                db.session.add(student_user)
                db.session.flush()
            student.user_id = student_user.id
        elif student.portal_user:
            student.portal_user.role = "student"
            student.portal_user.college_id = college.id
            student.portal_user.department_id = student.department_id
            student.portal_user.full_name = student.name
            student.portal_user.phone = student.phone

        if not student.parents:
            parent_username, parent_email = _parent_portal_identity(student.register_no)
            parent_user = User.query.filter_by(email=parent_email).first()
            if not parent_user:
                parent_user = User(
                    username=parent_username,
                    email=parent_email,
                    full_name=f"Parent of {student.name}",
                    role="parent",
                    college_id=college.id,
                    phone=f"+91-9200000{index:03d}",
                )
                parent_user.set_password("parent123")
                db.session.add(parent_user)
                db.session.flush()
            parent_profile = ParentProfile.query.filter_by(user_id=parent_user.id).first()
            if not parent_profile:
                parent_profile = ParentProfile(
                    college_id=college.id,
                    user_id=parent_user.id,
                    full_name=parent_user.full_name,
                    phone=parent_user.phone,
                    relationship="Parent",
                )
                db.session.add(parent_profile)
                db.session.flush()
            parent_profile.students.append(student)

    cse_staff.assigned_subjects = [subject_map["CSE201"], subject_map["CSE202"]]
    ece_staff.assigned_subjects = [subject_map["ECE201"], subject_map["ECE202"]]
    hod.assigned_subjects = [subject_map["CSE201"], subject_map["CSE202"]]

    if Attendance.query.filter_by(college_id=college.id).count() == 0:
        for student in students:
            for offset in range(30):
                attendance_date = date.today() - timedelta(days=offset)
                if attendance_date.weekday() >= 6:
                    continue
                db.session.add(
                    Attendance(
                        college_id=college.id,
                        student_id=student.id,
                        attendance_date=attendance_date,
                        status=choice(["Present", "Present", "Present", "Absent"]),
                    )
                )

    if ResultSummary.query.filter_by(college_id=college.id).count() == 0:
        for student in students:
            total = randint(320, 460)
            percentage = round(total / 5, 2)
            db.session.add(
                ResultSummary(
                    college_id=college.id,
                    student_id=student.id,
                    result_type="Internal",
                    exam_name="Cycle Test 1",
                    semester="Semester 1",
                    total_marks=total,
                    percentage=percentage,
                    result_status="Pass" if percentage >= 50 else "Reappear",
                )
            )

    if Mark.query.filter_by(college_id=college.id).count() == 0:
        department_subjects = defaultdict(list)
        for subject in subjects:
            department_subjects[subject.department_id].append(subject)
        for student in students:
            for subject in department_subjects.get(student.department_id, []):
                db.session.add(
                    Mark(
                        college_id=college.id,
                        student_id=student.id,
                        subject_id=subject.id,
                        exam_type="Internal",
                        marks_obtained=randint(55, min(subject.max_marks, 95)),
                    )
                )

    if FeeCategory.query.filter_by(college_id=college.id).count() == 0:
        categories = [
            FeeCategory(college_id=college.id, name="Tuition", description="Annual tuition fee", default_amount=45000),
            FeeCategory(college_id=college.id, name="Exam", description="Semester examination fee", default_amount=3500),
            FeeCategory(college_id=college.id, name="Library", description="Library access fee", default_amount=1500),
        ]
        db.session.add_all(categories)
        db.session.flush()
    else:
        categories = FeeCategory.query.filter_by(college_id=college.id).all()

    category_map = {category.name: category for category in categories}
    if StudentFee.query.filter_by(college_id=college.id).count() == 0:
        for student in students:
            tuition = StudentFee(
                college_id=college.id,
                student_id=student.id,
                fee_category_id=category_map["Tuition"].id,
                total_amount=category_map["Tuition"].default_amount,
                amount_paid=30000,
                due_date=date.today() + timedelta(days=20),
                status="pending",
                created_by_user_id=admin.id,
            )
            exam = StudentFee(
                college_id=college.id,
                student_id=student.id,
                fee_category_id=category_map["Exam"].id,
                total_amount=category_map["Exam"].default_amount,
                amount_paid=category_map["Exam"].default_amount,
                due_date=date.today() + timedelta(days=10),
                status="paid",
                created_by_user_id=admin.id,
            )
            db.session.add_all([tuition, exam])
            db.session.flush()
            db.session.add(FeePayment(college_id=college.id, student_fee_id=tuition.id, amount=30000, payment_method="online", reference=f"PAY-{student.register_no}-1"))
            db.session.add(FeePayment(college_id=college.id, student_fee_id=exam.id, amount=category_map["Exam"].default_amount, payment_method="cash", reference=f"PAY-{student.register_no}-2"))

    if TimeSlot.query.filter_by(college_id=college.id).count() == 0:
        slots = [
            TimeSlot(college_id=college.id, label="Slot 1", weekday="Monday", start_time=time(9, 0), end_time=time(10, 0)),
            TimeSlot(college_id=college.id, label="Slot 2", weekday="Monday", start_time=time(10, 15), end_time=time(11, 15)),
            TimeSlot(college_id=college.id, label="Slot 3", weekday="Tuesday", start_time=time(9, 0), end_time=time(10, 0)),
            TimeSlot(college_id=college.id, label="Slot 4", weekday="Wednesday", start_time=time(11, 30), end_time=time(12, 30)),
        ]
        db.session.add_all(slots)
        db.session.flush()
    else:
        slots = TimeSlot.query.filter_by(college_id=college.id).all()

    slot_map = {slot.label: slot for slot in slots}
    if TimetableEntry.query.filter_by(college_id=college.id).count() == 0:
        entries = [
            TimetableEntry(college_id=college.id, department_id=department_map["CSE"].id, year=2, subject_id=subject_map["CSE201"].id, staff_id=cse_staff.id, time_slot_id=slot_map["Slot 1"].id, room="C-201"),
            TimetableEntry(college_id=college.id, department_id=department_map["CSE"].id, year=3, subject_id=subject_map["CSE202"].id, staff_id=hod.id, time_slot_id=slot_map["Slot 2"].id, room="C-305"),
            TimetableEntry(college_id=college.id, department_id=department_map["ECE"].id, year=2, subject_id=subject_map["ECE201"].id, staff_id=ece_staff.id, time_slot_id=slot_map["Slot 3"].id, room="E-204"),
            TimetableEntry(college_id=college.id, department_id=department_map["ECE"].id, year=4, subject_id=subject_map["ECE202"].id, staff_id=ece_staff.id, time_slot_id=slot_map["Slot 4"].id, room="E-402"),
        ]
        db.session.add_all(entries)

    for user in User.query.filter(User.college_id.is_(None)).all():
        user.college_id = college.id
    for department in Department.query.filter(Department.college_id.is_(None)).all():
        department.college_id = college.id
    for student in Student.query.filter(Student.college_id.is_(None)).all():
        student.college_id = college.id
    for subject in Subject.query.filter(Subject.college_id.is_(None)).all():
        subject.college_id = college.id
    for record in Attendance.query.filter(Attendance.college_id.is_(None)).all():
        record.college_id = college.id
    for record in Mark.query.filter(Mark.college_id.is_(None)).all():
        record.college_id = college.id
    for record in ResultSummary.query.filter(ResultSummary.college_id.is_(None)).all():
        record.college_id = college.id
    for record in FeePayment.query.filter(FeePayment.college_id.is_(None)).all():
        record.college_id = college.id

    db.session.commit()
