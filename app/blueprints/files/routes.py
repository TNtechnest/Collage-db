from flask import Blueprint, current_app, flash, redirect, render_template, send_from_directory, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_

from app.extensions import db
from app.forms import UploadForm
from app.models import UploadedFile
from app.services.access import (
    college_has_feature,
    college_scoped_query,
    feature_required,
    get_accessible_student_ids,
    get_accessible_students,
    get_current_college,
    roles_required,
)
from app.services.helpers import flash_form_errors, log_activity
from app.services.storage import store_uploaded_file


files_bp = Blueprint("files", __name__, url_prefix="/files")


@files_bp.route("/", methods=["GET", "POST"])
@login_required
@roles_required("admin", "hod", "staff")
@feature_required("document_uploads", "event_gallery")
def file_center():
    form = UploadForm()
    accessible_students = get_accessible_students(current_user)
    accessible_student_ids = get_accessible_student_ids(current_user)
    form.student_id.choices = [(0, "No linked student")] + [
        (student.id, f"{student.name} ({student.register_no})") for student in accessible_students
    ]
    current_college = get_current_college(current_user)

    if form.validate_on_submit():
        if form.category.data == "student_document" and not form.student_id.data:
            flash("Select a student before uploading a student document.", "danger")
            return redirect(url_for("files.file_center"))
        if form.student_id.data and form.student_id.data not in (accessible_student_ids or []):
            flash("Select a valid student within your access scope.", "danger")
            return redirect(url_for("files.file_center"))
        if form.category.data == "event_photo" and not college_has_feature("event_gallery", current_user):
            flash("Event gallery uploads require the Pro plan.", "warning")
            return redirect(url_for("files.file_center"))

        original_name, stored_path = store_uploaded_file(form.file.data, current_college.code if current_college else "default", form.category.data)
        uploaded_file = UploadedFile(
            college_id=current_college.id if current_college else None,
            student_id=form.student_id.data or None,
            uploaded_by_user_id=current_user.id,
            category=form.category.data,
            original_filename=original_name,
            stored_filename=stored_path,
            content_type=form.file.data.content_type,
            description=(form.description.data or "").strip() or None,
        )
        db.session.add(uploaded_file)
        db.session.commit()
        log_activity(f"Uploaded file {uploaded_file.original_filename}", "Files", current_user.id)
        flash("File uploaded successfully.", "success")
        return redirect(url_for("files.file_center"))
    elif form.is_submitted():
        flash_form_errors(form)

    files = (
        college_scoped_query(UploadedFile, current_user)
        .filter(or_(UploadedFile.student_id.is_(None), UploadedFile.student_id.in_(accessible_student_ids or [0])))
        .order_by(UploadedFile.created_at.desc())
        .all()
    )
    return render_template("files/index.html", form=form, files=files)


@files_bp.route("/<int:file_id>/download")
@login_required
@roles_required("admin", "hod", "staff")
def download_file(file_id):
    accessible_student_ids = get_accessible_student_ids(current_user)
    file_record = college_scoped_query(UploadedFile, current_user).filter(UploadedFile.id == file_id).first_or_404()

    if file_record.student_id and file_record.student_id not in accessible_student_ids:
        flash("You do not have permission to access that file.", "danger")
        return redirect(url_for("files.file_center"))

    return send_from_directory(
        current_app.config["UPLOAD_FOLDER"],
        file_record.stored_filename,
        as_attachment=True,
        download_name=file_record.original_filename,
        mimetype=file_record.content_type,
    )
