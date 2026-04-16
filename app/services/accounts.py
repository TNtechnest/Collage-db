from app.extensions import db
from app.models import ParentProfile, User


def build_student_identity(register_no):
    slug = register_no.lower().strip()
    return slug, f"student.{slug}@college.local"


def build_parent_identity(register_no):
    slug = register_no.lower().strip()
    return f"parent.{slug}", f"parent.{slug}@college.local"


def ensure_student_portal_account(student, password=None):
    username, email = build_student_identity(student.register_no)
    user = student.portal_user

    if not user:
        user = User.query.filter_by(email=email).first()
    if not user:
        user = User(
            username=username,
            email=email,
            role="student",
            college_id=student.college_id,
            department_id=student.department_id,
        )
        db.session.add(user)
        db.session.flush()

    user.username = username
    user.email = email
    user.full_name = student.name
    user.phone = student.phone
    user.role = "student"
    user.college_id = student.college_id
    user.department_id = student.department_id
    if password and not user.password_hash:
        user.set_password(password)
    elif not user.password_hash:
        user.set_password(student.register_no.lower())

    student.user_id = user.id
    return user


def ensure_parent_profile(student, name=None, phone=None, email=None, relationship="Parent"):
    normalized_email = (email or "").strip().lower()
    normalized_name = (name or "").strip()
    normalized_phone = (phone or "").strip()

    parent_profile = student.parents[0] if student.parents else None
    user = parent_profile.user if parent_profile else None

    if normalized_email:
        user = User.query.filter_by(email=normalized_email).first() or user

    if not user:
        username, fallback_email = build_parent_identity(student.register_no)
        user = User.query.filter_by(email=normalized_email or fallback_email).first()
        if not user:
            user = User(
                username=username,
                email=normalized_email or fallback_email,
                role="parent",
                college_id=student.college_id,
            )
            user.set_password("parent123")
            db.session.add(user)
            db.session.flush()

    user.username = normalized_email or user.username or build_parent_identity(student.register_no)[0]
    user.email = normalized_email or user.email
    user.full_name = normalized_name or user.full_name or f"Parent of {student.name}"
    user.phone = normalized_phone or user.phone or student.phone
    user.role = "parent"
    user.college_id = student.college_id

    parent_profile = ParentProfile.query.filter_by(user_id=user.id).first() or parent_profile
    if not parent_profile:
        parent_profile = ParentProfile(
            college_id=student.college_id,
            user_id=user.id,
            full_name=user.full_name,
            phone=user.phone or student.phone or "",
            relationship=relationship,
        )
        db.session.add(parent_profile)
        db.session.flush()

    parent_profile.college_id = student.college_id
    parent_profile.full_name = normalized_name or parent_profile.full_name or user.full_name
    parent_profile.phone = normalized_phone or parent_profile.phone or user.phone or student.phone or ""
    parent_profile.relationship = relationship or parent_profile.relationship

    if student not in parent_profile.students:
        parent_profile.students.append(student)

    return parent_profile
