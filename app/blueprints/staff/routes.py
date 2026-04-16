from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_

from app.extensions import db
from app.forms import StaffForm
from app.models import Department, Subject, User
from app.services.access import admin_required, college_scoped_query, get_current_college
from app.services.helpers import flash_form_errors, log_activity


staff_bp = Blueprint("staff", __name__, url_prefix="/staff")


def _hydrate_staff_form(form):
    form.department_id.choices = [(0, "No Department")] + [
        (department.id, department.name)
        for department in college_scoped_query(Department, current_user).order_by(Department.name).all()
    ]
    form.subject_ids.choices = [
        (subject.id, f"{subject.name} ({subject.code})")
        for subject in college_scoped_query(Subject, current_user).order_by(Subject.name).all()
    ]


@staff_bp.route("/")
@login_required
@admin_required
def list_staff():
    page = request.args.get("page", 1, type=int)
    search = request.args.get("search", "", type=str).strip()

    query = college_scoped_query(User, current_user).filter(User.role.in_(["admin", "staff", "hod"]))
    if search:
        query = query.filter(
            or_(
                User.full_name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
                User.role.ilike(f"%{search}%"),
            )
        )

    staff_members = query.order_by(User.created_at.desc()).paginate(page=page, per_page=10)
    return render_template("staff/list.html", staff_members=staff_members, search=search)


@staff_bp.route("/add", methods=["GET", "POST"])
@login_required
@admin_required
def add_staff():
    form = StaffForm()
    _hydrate_staff_form(form)
    current_college = get_current_college(current_user)

    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        if User.query.filter_by(email=email).first():
            flash("A staff account with this email already exists.", "danger")
            return render_template("staff/form.html", form=form, title="Add Staff Member")
        if form.role.data == "staff" and not form.department_id.data:
            flash("Please choose a department for staff members.", "danger")
            return render_template("staff/form.html", form=form, title="Add Staff Member")
        if not form.password.data:
            flash("Please provide an initial password for the staff account.", "danger")
            return render_template("staff/form.html", form=form, title="Add Staff Member")

        user = User(
            username=email,
            email=email,
            full_name=form.full_name.data.strip(),
            phone=(form.phone.data or "").strip() or None,
            role=form.role.data,
            department_id=form.department_id.data or None,
            college_id=current_college.id if current_college else None,
        )
        user.set_password(form.password.data)
        if form.role.data in {"staff", "hod"}:
            user.assigned_subjects = college_scoped_query(Subject, current_user).filter(Subject.id.in_(form.subject_ids.data or [0])).all()
        db.session.add(user)
        db.session.commit()
        log_activity(f"Added {user.role} account for {user.display_name}", "Staff", current_user.id)
        flash("Staff account created successfully.", "success")
        return redirect(url_for("staff.list_staff"))
    if request.method == "POST":
        flash_form_errors(form)

    return render_template("staff/form.html", form=form, title="Add Staff Member")


@staff_bp.route("/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_staff(user_id):
    user = college_scoped_query(User, current_user).filter(User.id == user_id).first_or_404()
    form = StaffForm(obj=user)
    _hydrate_staff_form(form)

    if request.method == "GET":
        form.department_id.data = user.department_id or 0
        form.subject_ids.data = [subject.id for subject in user.assigned_subjects]

    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        duplicate = User.query.filter(User.email == email, User.id != user.id).first()
        if duplicate:
            flash("Another account is already using this email address.", "danger")
            return render_template("staff/form.html", form=form, title="Edit Staff Member")
        if form.role.data == "staff" and not form.department_id.data:
            flash("Please choose a department for staff members.", "danger")
            return render_template("staff/form.html", form=form, title="Edit Staff Member")

        user.full_name = form.full_name.data.strip()
        user.email = email
        user.username = email
        user.phone = (form.phone.data or "").strip() or None
        user.role = form.role.data
        user.department_id = form.department_id.data or None
        if form.password.data:
            user.set_password(form.password.data)
        if form.role.data in {"staff", "hod"}:
            user.assigned_subjects = college_scoped_query(Subject, current_user).filter(Subject.id.in_(form.subject_ids.data or [0])).all()
        else:
            user.assigned_subjects = []
        db.session.commit()
        log_activity(f"Updated {user.role} account for {user.display_name}", "Staff", current_user.id)
        flash("Staff account updated successfully.", "success")
        return redirect(url_for("staff.list_staff"))
    if request.method == "POST":
        flash_form_errors(form)

    return render_template("staff/form.html", form=form, title="Edit Staff Member")


@staff_bp.route("/<int:user_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_staff(user_id):
    user = college_scoped_query(User, current_user).filter(User.id == user_id).first_or_404()
    if user.id == current_user.id:
        flash("You cannot delete your own account while signed in.", "danger")
        return redirect(url_for("staff.list_staff"))
    if user.role == "admin" and college_scoped_query(User, current_user).filter_by(role="admin").count() <= 1:
        flash("At least one administrator account must remain active.", "danger")
        return redirect(url_for("staff.list_staff"))

    for activity in user.activities:
        activity.user_id = None
    user.assigned_subjects = []
    db.session.delete(user)
    db.session.commit()
    log_activity(f"Deleted account for {user.display_name}", "Staff", current_user.id)
    flash("Staff account deleted successfully.", "success")
    return redirect(url_for("staff.list_staff"))
