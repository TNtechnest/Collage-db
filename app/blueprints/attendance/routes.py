from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.forms import AttendanceForm
from app.models import Attendance, Department, Student
from app.services.access import college_scoped_query, employee_required, get_accessible_student_ids, get_college_departments
from app.services.helpers import flash_form_errors, log_activity
from app.services.notifications import queue_attendance_notification


attendance_bp = Blueprint("attendance", __name__, url_prefix="/attendance")


@attendance_bp.route("/", methods=["GET", "POST"])
@login_required
@employee_required
def manage_attendance():
    form = AttendanceForm()
    form.department_id.choices = [(dept.id, dept.name) for dept in get_college_departments(current_user)]
    selected_students = []
    selected_date = date.today()
    accessible_student_ids = get_accessible_student_ids(current_user)

    if not form.department_id.choices:
        flash("No departments are available for your account.", "warning")
        return render_template(
            "attendance/index.html",
            form=form,
            selected_students=[],
            existing_records={},
            attendance_history=[],
        )

    if request.method == "GET" and form.department_id.choices:
        form.department_id.data = request.args.get("department_id", form.department_id.choices[0][0], type=int)
        form.attendance_date.data = request.args.get("attendance_date", type=lambda v: date.fromisoformat(v)) or date.today()

    if form.validate_on_submit() or request.method == "GET":
        selected_date = form.attendance_date.data or date.today()
        selected_students = (
            college_scoped_query(Student, current_user)
            .filter(Student.department_id == form.department_id.data, Student.id.in_(accessible_student_ids or [0]))
            .order_by(Student.name)
            .all()
        )

        if request.method == "POST" and "save_attendance" in request.form:
            updated_records = []
            for student in selected_students:
                status = request.form.get(f"status_{student.id}", "Absent")
                record = college_scoped_query(Attendance, current_user).filter_by(
                    student_id=student.id,
                    attendance_date=selected_date,
                ).first()
                if record:
                    record.status = status
                else:
                    record = Attendance(
                        college_id=student.college_id,
                        student_id=student.id,
                        attendance_date=selected_date,
                        status=status,
                    )
                    db.session.add(record)
                updated_records.append((student, record))
            db.session.commit()
            for student, record in updated_records:
                queue_attendance_notification(student, record, actor=current_user)
            log_activity(
                f"Saved attendance for {selected_date.isoformat()} ({len(selected_students)} students)",
                "Attendance",
                current_user.id,
            )
            flash("Attendance updated successfully.", "success")
            return redirect(url_for("attendance.manage_attendance", department_id=form.department_id.data, attendance_date=selected_date.isoformat()))
    elif request.method == "POST":
        flash_form_errors(form)

    existing_records = {
        record.student_id: record.status
        for record in college_scoped_query(Attendance, current_user)
        .filter(Attendance.attendance_date == selected_date, Attendance.student_id.in_(accessible_student_ids or [0]))
        .all()
    }

    attendance_history = (
        college_scoped_query(Attendance, current_user)
        .join(Student)
        .join(Department)
        .filter(Attendance.student_id.in_(accessible_student_ids or [0]))
        .order_by(Attendance.attendance_date.desc(), Student.name)
        .limit(20)
        .all()
    )

    return render_template(
        "attendance/index.html",
        form=form,
        selected_students=selected_students,
        existing_records=existing_records,
        attendance_history=attendance_history,
    )
