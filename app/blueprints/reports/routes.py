from datetime import date

from flask import Blueprint, render_template, request, send_file
from flask_login import current_user, login_required

from app.forms import ReportFilterForm
from app.models import Attendance, ResultSummary, Student
from app.services.access import college_scoped_query, employee_required, get_accessible_student_ids, get_college_departments, get_current_college
from app.services.helpers import flash_form_errors
from app.services.reporting import build_excel_report, build_pdf_report


reports_bp = Blueprint("reports", __name__, url_prefix="/reports")


def _filtered_data(form):
    accessible_student_ids = get_accessible_student_ids(current_user)
    query = college_scoped_query(Student, current_user).filter(Student.id.in_(accessible_student_ids or [0]))
    if form.department_id.data:
        query = query.filter_by(department_id=form.department_id.data)
    students = query.order_by(Student.name).all()
    student_ids = [student.id for student in students] or [0]

    attendance_records = college_scoped_query(Attendance, current_user).filter(
        Attendance.student_id.in_(student_ids),
        Attendance.attendance_date >= form.start_date.data,
        Attendance.attendance_date <= form.end_date.data,
    ).all()

    result_summaries = college_scoped_query(ResultSummary, current_user).filter(ResultSummary.student_id.in_(student_ids)).all()
    return students, attendance_records, result_summaries


def _build_export_filter():
    form = ReportFilterForm()
    form.department_id.data = request.args.get("department_id", 0, type=int)
    form.start_date.data = request.args.get(
        "start_date",
        type=lambda value: date.fromisoformat(value),
    ) or date.today().replace(day=1)
    form.end_date.data = request.args.get(
        "end_date",
        type=lambda value: date.fromisoformat(value),
    ) or date.today()
    return form


@reports_bp.route("/", methods=["GET", "POST"])
@login_required
@employee_required
def report_center():
    form = ReportFilterForm()
    form.department_id.choices = [(0, "All Departments")] + [
        (dept.id, dept.name) for dept in get_college_departments(current_user)
    ]

    if request.method == "GET":
        form.start_date.data = date.today().replace(day=1)
        form.end_date.data = date.today()
        form.department_id.data = 0

    students, attendance_records, result_summaries = [], [], []
    if form.validate_on_submit() or request.method == "GET":
        students, attendance_records, result_summaries = _filtered_data(form)
    elif request.method == "POST":
        flash_form_errors(form)

    return render_template(
        "reports/index.html",
        form=form,
        students=students,
        attendance_records=attendance_records,
        result_summaries=result_summaries,
    )


@reports_bp.route("/export/excel")
@login_required
@employee_required
def export_excel():
    form = _build_export_filter()
    students, attendance_records, result_summaries = _filtered_data(form)
    output = build_excel_report(students, attendance_records, result_summaries)
    return send_file(
        output,
        as_attachment=True,
        download_name="college_report.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@reports_bp.route("/export/pdf")
@login_required
@employee_required
def export_pdf():
    form = _build_export_filter()
    students, attendance_records, result_summaries = _filtered_data(form)
    college = get_current_college(current_user)
    output = build_pdf_report(students, attendance_records, result_summaries, college.name if college else "College")
    return send_file(output, as_attachment=True, download_name="college_report.pdf", mimetype="application/pdf")
