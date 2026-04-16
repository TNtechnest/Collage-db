from flask import Blueprint, flash, redirect, render_template, send_file, url_for
from flask_login import current_user, login_required

from app.models import TimetableEntry, UploadedFile
from app.services.access import college_scoped_query, get_current_college, roles_required
from app.services.reporting import build_student_report_pdf


portal_bp = Blueprint("portal", __name__, url_prefix="/portal")


def _current_student():
    student = current_user.student_profile
    if not student:
        flash("No student profile is linked to this account.", "warning")
        return None
    return student


def _parent_students():
    if not current_user.parent_profile:
        flash("No parent profile is linked to this account.", "warning")
        return []
    return list(current_user.parent_profile.students)


@portal_bp.route("/student")
@login_required
@roles_required("student")
def student_dashboard():
    student = _current_student()
    if not student:
        return redirect(url_for("auth.logout"))

    timetable_entries = (
        college_scoped_query(TimetableEntry, current_user)
        .filter_by(department_id=student.department_id, year=student.year)
        .join(TimetableEntry.time_slot)
        .all()
    )
    uploaded_files = college_scoped_query(UploadedFile, current_user).filter_by(student_id=student.id).all()
    recent_results = sorted(student.summaries, key=lambda item: item.created_at, reverse=True)[:5]
    recent_marks = sorted(student.marks, key=lambda item: item.updated_at, reverse=True)[:8]

    return render_template(
        "portal/student_dashboard.html",
        student=student,
        timetable_entries=timetable_entries,
        uploaded_files=uploaded_files,
        recent_results=recent_results,
        recent_marks=recent_marks,
    )


@portal_bp.route("/parent")
@login_required
@roles_required("parent")
def parent_dashboard():
    students = _parent_students()
    child_summaries = []
    for student in students:
        latest_result = sorted(student.summaries, key=lambda item: item.created_at, reverse=True)
        child_summaries.append(
            {
                "student": student,
                "latest_result": latest_result[0] if latest_result else None,
            }
        )

    return render_template("portal/parent_dashboard.html", child_summaries=child_summaries)


@portal_bp.route("/profile")
@login_required
@roles_required("student", "parent")
def profile():
    student = current_user.student_profile if current_user.role == "student" else None
    parent_profile = current_user.parent_profile if current_user.role == "parent" else None
    return render_template("portal/profile.html", student=student, parent_profile=parent_profile)


@portal_bp.route("/student/report.pdf")
@login_required
@roles_required("student")
def student_report():
    student = _current_student()
    if not student:
        return redirect(url_for("auth.logout"))
    college = get_current_college(current_user)
    output = build_student_report_pdf(student, college.name if college else "College")
    return send_file(output, as_attachment=True, download_name=f"{student.register_no}_report.pdf", mimetype="application/pdf")


@portal_bp.route("/parent/<int:student_id>/report.pdf")
@login_required
@roles_required("parent")
def parent_student_report(student_id):
    students = _parent_students()
    student = next((item for item in students if item.id == student_id), None)
    if not student:
        flash("You do not have access to that student report.", "danger")
        return redirect(url_for("portal.parent_dashboard"))
    college = get_current_college(current_user)
    output = build_student_report_pdf(student, college.name if college else "College")
    return send_file(output, as_attachment=True, download_name=f"{student.register_no}_report.pdf", mimetype="application/pdf")
