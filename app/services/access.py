from functools import wraps

from flask import flash, redirect, url_for
from flask_login import current_user

from app.models import College, Department, Student, Subject, User, staff_subject_assignments


EMPLOYEE_ROLES = {"admin", "hod", "staff"}
PORTAL_ROLES = {"student", "parent"}
ROLE_LABELS = {
    "admin": "Administrator",
    "hod": "Head of Department",
    "staff": "Staff",
    "student": "Student",
    "parent": "Parent",
}


def get_current_college(user=None):
    active_user = user or (current_user if getattr(current_user, "is_authenticated", False) else None)
    if active_user and active_user.college_id:
        return College.query.get(active_user.college_id)
    return College.query.order_by(College.id).first()


def get_plan_features(user=None):
    college = get_current_college(user)
    plan = college.active_plan if college else None
    return set(plan.features or []) if plan else set()


def college_has_feature(feature_key, user=None):
    return feature_key in get_plan_features(user)


def feature_required(*feature_keys):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login"))
            if not any(college_has_feature(feature_key, current_user) for feature_key in feature_keys):
                flash("Your subscription plan does not include that module.", "warning")
                return redirect(url_for(user_home_endpoint(current_user)))
            return view_func(*args, **kwargs)

        return wrapped_view

    return decorator


def college_scoped_query(model, user=None, query=None):
    scoped_query = query or model.query
    college = get_current_college(user)
    if college and hasattr(model, "college_id"):
        scoped_query = scoped_query.filter(model.college_id == college.id)
    return scoped_query


def roles_required(*allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login"))
            if current_user.role not in allowed_roles:
                flash("You do not have permission to access that page.", "danger")
                if current_user.role == "student":
                    return redirect(url_for("portal.student_dashboard"))
                if current_user.role == "parent":
                    return redirect(url_for("portal.parent_dashboard"))
                return redirect(url_for("main.dashboard"))
            return view_func(*args, **kwargs)

        return wrapped_view

    return decorator


admin_required = roles_required("admin")


def employee_required(view_func):
    return roles_required("admin", "hod", "staff")(view_func)


def get_college_departments(user):
    college = get_current_college(user)
    if not college:
        return []
    query = college_scoped_query(Department, user)
    if user.role == "hod" and user.department_id:
        query = query.filter(Department.id == user.department_id)
    elif user.role == "staff":
        department_ids = {subject.department_id for subject in user.assigned_subjects if subject.department_id}
        if department_ids:
            query = query.filter(Department.id.in_(department_ids))
        else:
            query = query.filter(Department.id == 0)
    elif user.role == "student" and user.student_profile:
        query = query.filter(Department.id == user.student_profile.department_id)
    elif user.role == "parent" and user.parent_profile:
        department_ids = {student.department_id for student in user.parent_profile.students}
        query = query.filter(Department.id.in_(department_ids or [0]))
    return query.order_by(Department.name).all()


def get_accessible_department_ids(user):
    return [department.id for department in get_college_departments(user)]


def get_accessible_subjects(user):
    college = get_current_college(user)
    if not college:
        return []

    query = college_scoped_query(Subject, user)
    if user.role == "admin":
        return query.order_by(Subject.name).all()
    if user.role == "hod" and user.department_id:
        return query.filter(Subject.department_id == user.department_id).order_by(Subject.name).all()
    if user.role == "staff":
        return (
            query.join(
                staff_subject_assignments,
                Subject.id == staff_subject_assignments.c.subject_id,
            )
            .filter(staff_subject_assignments.c.user_id == user.id)
            .order_by(Subject.name)
            .all()
        )
    if user.role == "student" and user.student_profile:
        return query.filter(Subject.department_id == user.student_profile.department_id).order_by(Subject.name).all()
    if user.role == "parent" and user.parent_profile:
        department_ids = {student.department_id for student in user.parent_profile.students}
        return query.filter(Subject.department_id.in_(department_ids or [0])).order_by(Subject.name).all()
    return []


def get_accessible_subject_ids(user):
    return [subject.id for subject in get_accessible_subjects(user)]


def get_accessible_students(user):
    college = get_current_college(user)
    if not college:
        return []

    query = college_scoped_query(Student, user)
    if user.role == "admin":
        return query.order_by(Student.name).all()
    if user.role == "hod" and user.department_id:
        return query.filter(Student.department_id == user.department_id).order_by(Student.name).all()
    if user.role == "staff":
        department_ids = sorted({subject.department_id for subject in user.assigned_subjects if subject.department_id})
        return query.filter(Student.department_id.in_(department_ids or [0])).order_by(Student.name).all()
    if user.role == "student" and user.student_profile:
        return query.filter(Student.id == user.student_profile.id).all()
    if user.role == "parent" and user.parent_profile:
        student_ids = [student.id for student in user.parent_profile.students]
        return query.filter(Student.id.in_(student_ids or [0])).order_by(Student.name).all()
    return []


def get_accessible_student_ids(user):
    return [student.id for student in get_accessible_students(user)]


def get_college_users(user, roles=None):
    college = get_current_college(user)
    if not college:
        return []
    query = college_scoped_query(User, user)
    if roles:
        query = query.filter(User.role.in_(roles))
    if user.role == "hod" and user.department_id:
        query = query.filter((User.department_id == user.department_id) | (User.role == "admin"))
    return query.order_by(User.full_name, User.username).all()


def user_can_access_subject(user, subject_id):
    return subject_id in get_accessible_subject_ids(user)


def user_can_access_student(user, student):
    if not student or student.id not in get_accessible_student_ids(user):
        return False
    college = get_current_college(user)
    return not college or student.college_id == college.id


def user_can_manage_department(user, department_id):
    if user.role == "admin":
        return True
    if user.role == "hod":
        return user.department_id == department_id
    if user.role == "staff":
        return department_id in get_accessible_department_ids(user)
    return False


def user_home_endpoint(user):
    if user.role == "student":
        return "portal.student_dashboard"
    if user.role == "parent":
        return "portal.parent_dashboard"
    return "main.dashboard"
