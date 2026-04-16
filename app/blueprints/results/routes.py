import os

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.forms import InternalMarkForm, UniversityUploadForm
from app.models import Mark, ResultSummary, Subject
from app.services.access import (
    college_scoped_query,
    employee_required,
    get_accessible_student_ids,
    get_accessible_students,
    get_accessible_subjects,
    get_current_college,
)
from app.services.helpers import flash_form_errors, log_activity
from app.services.notifications import queue_result_notification
from app.services.reporting import parse_university_excel


results_bp = Blueprint("results", __name__, url_prefix="/results")


def _hydrate_mark_form(form):
    students = get_accessible_students(current_user)
    subjects = get_accessible_subjects(current_user)
    form.student_id.choices = [
        (student.id, f"{student.name} ({student.register_no})") for student in students
    ]
    form.subject_id.choices = [
        (subject.id, f"{subject.name} ({subject.code})") for subject in subjects
    ]
    return students, subjects


@results_bp.route("/", methods=["GET", "POST"])
@login_required
@employee_required
def manage_results():
    mark_form = InternalMarkForm(prefix="mark")
    upload_form = UniversityUploadForm(prefix="upload")
    accessible_students, accessible_subjects = _hydrate_mark_form(mark_form)
    accessible_student_ids = get_accessible_student_ids(current_user)
    accessible_subject_ids = [subject.id for subject in accessible_subjects]
    current_college = get_current_college(current_user)
    can_upload_university = current_user.role == "admin"

    if mark_form.submit.data and mark_form.validate_on_submit():
        if mark_form.subject_id.data not in accessible_subject_ids:
            flash("You do not have access to that subject.", "danger")
            return redirect(url_for("results.manage_results"))

        subject = college_scoped_query(Subject, current_user).filter(Subject.id == mark_form.subject_id.data).first()
        student = next((item for item in accessible_students if item.id == mark_form.student_id.data), None)
        if not subject or not student:
            flash("Please select a valid student and subject.", "danger")
            return redirect(url_for("results.manage_results"))

        if subject.department_id and student.department_id != subject.department_id:
            flash("The selected subject does not belong to the student's department.", "danger")
            return redirect(url_for("results.manage_results"))

        mark = Mark.query.filter_by(
            college_id=current_college.id if current_college else None,
            student_id=mark_form.student_id.data,
            subject_id=mark_form.subject_id.data,
            exam_type=mark_form.exam_type.data,
        ).first()
        if mark:
            mark.marks_obtained = mark_form.marks_obtained.data
        else:
            db.session.add(
                Mark(
                    college_id=current_college.id if current_college else None,
                    student_id=mark_form.student_id.data,
                    subject_id=mark_form.subject_id.data,
                    exam_type=mark_form.exam_type.data,
                    marks_obtained=mark_form.marks_obtained.data,
                )
            )
        db.session.commit()

        student_marks = Mark.query.filter_by(
            student_id=mark_form.student_id.data,
            exam_type=mark_form.exam_type.data,
        ).all()
        total = sum(item.marks_obtained for item in student_marks)
        max_total = sum(item.subject.max_marks for item in student_marks) or (subject.max_marks if subject else 100)
        percentage = round((total / max_total) * 100, 2) if max_total else 0
        summary = ResultSummary.query.filter_by(
            college_id=current_college.id if current_college else None,
            student_id=mark_form.student_id.data,
            result_type="Internal",
            exam_name=mark_form.exam_type.data,
        ).first()
        if summary:
            summary.total_marks = total
            summary.percentage = percentage
            summary.semester = "Internal"
            summary.result_status = "Pass" if percentage >= 50 else "Reappear"
        else:
            db.session.add(
                ResultSummary(
                    college_id=current_college.id if current_college else None,
                    student_id=mark_form.student_id.data,
                    result_type="Internal",
                    exam_name=mark_form.exam_type.data,
                    semester="Internal",
                    total_marks=total,
                    percentage=percentage,
                    result_status="Pass" if percentage >= 50 else "Reappear",
                )
            )
        db.session.commit()
        latest_summary = ResultSummary.query.filter_by(
            college_id=current_college.id if current_college else None,
            student_id=student.id,
            result_type="Internal",
            exam_name=mark_form.exam_type.data,
        ).first()
        if latest_summary:
            queue_result_notification(student, latest_summary, actor=current_user)
        log_activity(
            f"Saved internal marks for {subject.name}",
            "Results",
            current_user.id,
        )
        flash("Internal result saved successfully.", "success")
        return redirect(url_for("results.manage_results"))
    elif request.method == "POST" and mark_form.submit.data:
        flash_form_errors(mark_form)

    if upload_form.submit.data:
        if not can_upload_university:
            flash("Only administrators can upload university results.", "danger")
            return redirect(url_for("results.manage_results"))
        if upload_form.validate_on_submit():
            os.makedirs(current_app.config["UPLOAD_FOLDER"], exist_ok=True)
            records = parse_university_excel(
                upload_form.excel_file.data,
                upload_form.exam_name.data.strip(),
                upload_form.semester.data.strip(),
                current_college.id if current_college else None,
            )
            if not records:
                flash("No matching students were found in the uploaded file.", "warning")
            else:
                synced_records = []
                for record in records:
                    existing = ResultSummary.query.filter_by(
                        college_id=record.college_id,
                        student_id=record.student_id,
                        result_type=record.result_type,
                        exam_name=record.exam_name,
                        semester=record.semester,
                    ).first()
                    if existing:
                        existing.total_marks = record.total_marks
                        existing.percentage = record.percentage
                        existing.result_status = record.result_status
                        synced_records.append(existing)
                    else:
                        db.session.add(record)
                        synced_records.append(record)
                db.session.commit()
                for summary in synced_records:
                    queue_result_notification(summary.student, summary, actor=current_user)
                log_activity(f"Uploaded {len(synced_records)} university results", "Results", current_user.id)
                flash(f"Uploaded {len(synced_records)} university results successfully.", "success")
            return redirect(url_for("results.manage_results"))
        flash_form_errors(upload_form)

    marks_query = college_scoped_query(Mark, current_user).filter(Mark.student_id.in_(accessible_student_ids or [0]))
    if current_user.role != "admin":
        marks_query = marks_query.filter(Mark.subject_id.in_(accessible_subject_ids or [0]))

    marks = marks_query.order_by(Mark.updated_at.desc()).limit(15).all()
    results_query = college_scoped_query(ResultSummary, current_user).filter(ResultSummary.student_id.in_(accessible_student_ids or [0]))
    internal_results = results_query.filter_by(result_type="Internal").order_by(ResultSummary.updated_at.desc()).all()
    university_results = results_query.filter_by(result_type="University").order_by(ResultSummary.updated_at.desc()).all()

    return render_template(
        "results/index.html",
        mark_form=mark_form,
        upload_form=upload_form,
        internal_results=internal_results,
        university_results=university_results,
        marks=marks,
        can_upload_university=can_upload_university,
        accessible_subjects=accessible_subjects,
    )
