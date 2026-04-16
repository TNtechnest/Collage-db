from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_

from app.extensions import db
from app.forms import SubjectForm
from app.models import Department, Subject, staff_subject_assignments
from app.services.access import (
    college_scoped_query,
    employee_required,
    get_college_departments,
    get_current_college,
    roles_required,
    user_can_manage_department,
)
from app.services.helpers import flash_form_errors, log_activity


subjects_bp = Blueprint("subjects", __name__, url_prefix="/subjects")


def _hydrate_subject_form(form):
    form.department_id.choices = [
        (department.id, department.name)
        for department in get_college_departments(current_user)
    ]


@subjects_bp.route("/")
@login_required
@employee_required
def list_subjects():
    page = request.args.get("page", 1, type=int)
    search = request.args.get("search", "", type=str).strip()
    department_id = request.args.get("department_id", 0, type=int)

    query = college_scoped_query(Subject, current_user).join(Department, isouter=True)
    if current_user.role == "hod" and current_user.department_id:
        query = query.filter(Subject.department_id == current_user.department_id)
    elif current_user.role == "staff":
        query = query.join(
            staff_subject_assignments,
            Subject.id == staff_subject_assignments.c.subject_id,
        ).filter(staff_subject_assignments.c.user_id == current_user.id)
    if search:
        query = query.filter(
            or_(
                Subject.name.ilike(f"%{search}%"),
                Subject.code.ilike(f"%{search}%"),
                Department.name.ilike(f"%{search}%"),
            )
        )
    if department_id:
        query = query.filter(Subject.department_id == department_id)

    subjects = query.order_by(Subject.name).paginate(page=page, per_page=10)
    departments = get_college_departments(current_user)
    return render_template(
        "subjects/list.html",
        subjects=subjects,
        departments=departments,
        search=search,
        selected_department=department_id,
    )


@subjects_bp.route("/add", methods=["GET", "POST"])
@login_required
@roles_required("admin", "hod")
def add_subject():
    form = SubjectForm()
    _hydrate_subject_form(form)
    current_college = get_current_college(current_user)

    if form.validate_on_submit():
        if not user_can_manage_department(current_user, form.department_id.data):
            flash("You cannot create subjects for that department.", "danger")
            return render_template("subjects/form.html", form=form, title="Add Subject")

        code = form.code.data.strip().upper()
        duplicate = college_scoped_query(Subject, current_user).filter_by(code=code).first()
        if duplicate:
            flash("Subject code already exists.", "danger")
            return render_template("subjects/form.html", form=form, title="Add Subject")

        subject = Subject(
            name=form.name.data.strip(),
            code=code,
            department_id=form.department_id.data,
            max_marks=form.max_marks.data,
            college_id=current_college.id if current_college else None,
        )
        db.session.add(subject)
        db.session.commit()
        log_activity(f"Added subject {subject.name}", "Subjects", current_user.id)
        flash("Subject created successfully.", "success")
        return redirect(url_for("subjects.list_subjects"))
    if request.method == "POST":
        flash_form_errors(form)

    return render_template("subjects/form.html", form=form, title="Add Subject")


@subjects_bp.route("/<int:subject_id>/edit", methods=["GET", "POST"])
@login_required
@roles_required("admin", "hod")
def edit_subject(subject_id):
    subject = college_scoped_query(Subject, current_user).filter(Subject.id == subject_id).first_or_404()
    if not user_can_manage_department(current_user, subject.department_id):
        flash("You cannot edit that subject.", "danger")
        return redirect(url_for("subjects.list_subjects"))

    form = SubjectForm(obj=subject)
    _hydrate_subject_form(form)

    if request.method == "GET":
        form.department_id.data = subject.department_id

    if form.validate_on_submit():
        if not user_can_manage_department(current_user, form.department_id.data):
            flash("You cannot move subjects into that department.", "danger")
            return render_template("subjects/form.html", form=form, title="Edit Subject")

        code = form.code.data.strip().upper()
        duplicate = college_scoped_query(Subject, current_user).filter(Subject.code == code, Subject.id != subject.id).first()
        if duplicate:
            flash("Another subject is already using that code.", "danger")
            return render_template("subjects/form.html", form=form, title="Edit Subject")

        subject.name = form.name.data.strip()
        subject.code = code
        subject.department_id = form.department_id.data
        subject.max_marks = form.max_marks.data
        db.session.commit()
        log_activity(f"Updated subject {subject.name}", "Subjects", current_user.id)
        flash("Subject updated successfully.", "success")
        return redirect(url_for("subjects.list_subjects"))
    if request.method == "POST":
        flash_form_errors(form)

    return render_template("subjects/form.html", form=form, title="Edit Subject")


@subjects_bp.route("/<int:subject_id>/delete", methods=["POST"])
@login_required
@roles_required("admin", "hod")
def delete_subject(subject_id):
    subject = college_scoped_query(Subject, current_user).filter(Subject.id == subject_id).first_or_404()
    if not user_can_manage_department(current_user, subject.department_id):
        flash("You cannot delete that subject.", "danger")
        return redirect(url_for("subjects.list_subjects"))
    if subject.marks:
        flash("This subject already has marks records and cannot be deleted.", "danger")
        return redirect(url_for("subjects.list_subjects"))
    if subject.assigned_staff:
        flash("Please unassign staff from this subject before deleting it.", "danger")
        return redirect(url_for("subjects.list_subjects"))

    db.session.delete(subject)
    db.session.commit()
    log_activity(f"Deleted subject {subject.name}", "Subjects", current_user.id)
    flash("Subject deleted successfully.", "success")
    return redirect(url_for("subjects.list_subjects"))
