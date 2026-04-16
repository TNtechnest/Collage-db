from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.forms import DepartmentForm, SettingsForm
from app.models import College, Department, Setting
from app.services.access import admin_required, college_scoped_query, get_current_college
from app.services.helpers import flash_form_errors, log_activity


settings_bp = Blueprint("settings", __name__, url_prefix="/settings")


@settings_bp.route("/", methods=["GET", "POST"])
@login_required
@admin_required
def manage_settings():
    settings_form = SettingsForm(prefix="settings")
    department_form = DepartmentForm(prefix="department")
    college = get_current_college(current_user)

    college_name_setting = Setting.query.filter_by(key="college_name").first()
    if request.method == "GET" and college:
        settings_form.college_name.data = college.name
        settings_form.college_code.data = college.code
        settings_form.contact_email.data = college.contact_email
        settings_form.contact_phone.data = college.contact_phone
    elif college_name_setting and not settings_form.college_name.data:
        settings_form.college_name.data = college_name_setting.value

    if settings_form.submit.data and settings_form.validate_on_submit():
        if not college:
            college = College(
                name=settings_form.college_name.data.strip(),
                code=settings_form.college_code.data.strip().upper(),
            )
            db.session.add(college)
            db.session.flush()

        college.name = settings_form.college_name.data.strip()
        college.code = settings_form.college_code.data.strip().upper()
        college.contact_email = (settings_form.contact_email.data or "").strip() or None
        college.contact_phone = (settings_form.contact_phone.data or "").strip() or None
        current_user.college_id = college.id

        if college_name_setting:
            college_name_setting.value = college.name
        else:
            db.session.add(Setting(key="college_name", value=college.name))
        db.session.commit()
        log_activity("Updated college settings", "Settings", current_user.id)
        flash("College settings saved successfully.", "success")
        return redirect(url_for("settings.manage_settings"))
    elif settings_form.submit.data and settings_form.is_submitted():
        flash_form_errors(settings_form)

    if department_form.submit.data and department_form.validate_on_submit():
        existing_department = college_scoped_query(Department, current_user).filter(
            (Department.name == department_form.name.data.strip()) |
            (Department.code == department_form.code.data.strip().upper())
        ).first()
        if existing_department:
            flash("Department name or code already exists.", "danger")
            return redirect(url_for("settings.manage_settings"))

        department = Department(
            name=department_form.name.data.strip(),
            code=department_form.code.data.strip().upper(),
            college_id=college.id if college else None,
        )
        db.session.add(department)
        db.session.commit()
        log_activity(f"Added department {department.name}", "Settings", current_user.id)
        flash("Department added successfully.", "success")
        return redirect(url_for("settings.manage_settings"))
    elif department_form.submit.data and department_form.is_submitted():
        flash_form_errors(department_form)

    departments = college_scoped_query(Department, current_user).order_by(Department.name).all()
    return render_template(
        "settings/index.html",
        settings_form=settings_form,
        department_form=department_form,
        departments=departments,
    )
