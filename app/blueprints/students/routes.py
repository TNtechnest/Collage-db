from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_

from app.extensions import db
from app.forms import StudentForm
from app.models import Department, Student
from app.services.accounts import ensure_parent_profile, ensure_student_portal_account
from app.services.access import (
    college_scoped_query,
    employee_required,
    get_accessible_student_ids,
    get_college_departments,
    get_current_college,
    roles_required,
    user_can_manage_department,
)
from app.services.helpers import flash_form_errors, log_activity


students_bp = Blueprint("students", __name__, url_prefix="/students")


def _assign_department_choices(form):
    form.department_id.choices = [(dept.id, dept.name) for dept in get_college_departments(current_user)]


def _student_query():
    accessible_student_ids = get_accessible_student_ids(current_user) or [0]
    return college_scoped_query(Student, current_user).filter(Student.id.in_(accessible_student_ids))


@students_bp.route("/")
@login_required
@employee_required
def list_students():
    page = request.args.get("page", 1, type=int)
    search = request.args.get("search", "", type=str).strip()
    department_id = request.args.get("department_id", 0, type=int)
    year = request.args.get("year", 0, type=int)

    query = _student_query().join(Department)
    if search:
        query = query.filter(
            or_(Student.name.ilike(f"%{search}%"), Student.register_no.ilike(f"%{search}%"))
        )
    if department_id:
        query = query.filter(Student.department_id == department_id)
    if year:
        query = query.filter(Student.year == year)

    students = query.order_by(Student.created_at.desc()).paginate(page=page, per_page=10)
    departments = get_college_departments(current_user)
    return render_template(
        "students/list.html",
        students=students,
        departments=departments,
        search=search,
        selected_department=department_id,
        selected_year=year,
    )


@students_bp.route("/add", methods=["GET", "POST"])
@login_required
@roles_required("admin", "hod")
def add_student():
    form = StudentForm()
    _assign_department_choices(form)
    current_college = get_current_college(current_user)

    if form.validate_on_submit():
        if not user_can_manage_department(current_user, form.department_id.data):
            flash("You cannot manage students outside your permitted departments.", "danger")
            return render_template("students/form.html", form=form, title="Add Student")

        existing_student = college_scoped_query(Student, current_user).filter_by(register_no=form.register_no.data.strip()).first()
        if existing_student:
            flash("Register number already exists. Please use a unique value.", "danger")
            return render_template("students/form.html", form=form, title="Add Student")

        student = Student(
            name=form.name.data.strip(),
            register_no=form.register_no.data.strip(),
            phone=(form.phone.data or "").strip() or None,
            department_id=form.department_id.data,
            year=form.year.data,
            college_id=current_college.id if current_college else None,
        )
        db.session.add(student)
        db.session.flush()
        ensure_student_portal_account(student)
        if any([form.parent_name.data, form.parent_phone.data, form.parent_email.data]):
            ensure_parent_profile(
                student,
                name=form.parent_name.data,
                phone=form.parent_phone.data,
                email=form.parent_email.data,
            )
        db.session.commit()
        log_activity(f"Added student {student.name}", "Students", current_user.id)
        flash("Student added successfully.", "success")
        return redirect(url_for("students.list_students"))
    if request.method == "POST":
        flash_form_errors(form)

    return render_template("students/form.html", form=form, title="Add Student")


@students_bp.route("/<int:student_id>/edit", methods=["GET", "POST"])
@login_required
@roles_required("admin", "hod")
def edit_student(student_id):
    student = _student_query().filter(Student.id == student_id).first_or_404()
    if not user_can_manage_department(current_user, student.department_id):
        flash("You cannot edit that student record.", "danger")
        return redirect(url_for("students.list_students"))

    form = StudentForm(obj=student)
    _assign_department_choices(form)

    if request.method == "GET" and student.parents:
        parent_profile = student.parents[0]
        form.parent_name.data = parent_profile.full_name
        form.parent_phone.data = parent_profile.phone
        form.parent_email.data = parent_profile.user.email if parent_profile.user else ""

    if form.validate_on_submit():
        if not user_can_manage_department(current_user, form.department_id.data):
            flash("You cannot move students into that department.", "danger")
            return render_template("students/form.html", form=form, title="Edit Student")

        duplicate = Student.query.filter(
            Student.register_no == form.register_no.data.strip(),
            Student.id != student.id,
            Student.college_id == student.college_id,
        ).first()
        if duplicate:
            flash("Register number already belongs to another student.", "danger")
            return render_template("students/form.html", form=form, title="Edit Student")

        student.name = form.name.data.strip()
        student.register_no = form.register_no.data.strip()
        student.phone = (form.phone.data or "").strip() or None
        student.department_id = form.department_id.data
        student.year = form.year.data
        ensure_student_portal_account(student)
        if any([form.parent_name.data, form.parent_phone.data, form.parent_email.data]) or student.parents:
            ensure_parent_profile(
                student,
                name=form.parent_name.data,
                phone=form.parent_phone.data,
                email=form.parent_email.data,
            )
        db.session.commit()
        log_activity(f"Updated student {student.name}", "Students", current_user.id)
        flash("Student updated successfully.", "success")
        return redirect(url_for("students.list_students"))
    if request.method == "POST":
        flash_form_errors(form)

    return render_template("students/form.html", form=form, title="Edit Student")


@students_bp.route("/<int:student_id>/delete", methods=["POST"])
@login_required
@roles_required("admin", "hod")
def delete_student(student_id):
    student = _student_query().filter(Student.id == student_id).first_or_404()
    if not user_can_manage_department(current_user, student.department_id):
        flash("You cannot delete that student record.", "danger")
        return redirect(url_for("students.list_students"))

    portal_user = student.portal_user
    linked_parents = list(student.parents)
    student.user_id = None

    for parent_profile in linked_parents:
        if student in parent_profile.students:
            parent_profile.students.remove(student)
        if not parent_profile.students:
            if parent_profile.user:
                for activity in parent_profile.user.activities:
                    activity.user_id = None
                db.session.delete(parent_profile.user)
            db.session.delete(parent_profile)

    if portal_user:
        for activity in portal_user.activities:
            activity.user_id = None
        db.session.delete(portal_user)

    db.session.delete(student)
    db.session.commit()
    log_activity(f"Deleted student {student.name}", "Students", current_user.id)
    flash("Student removed successfully.", "success")
    return redirect(url_for("students.list_students"))
