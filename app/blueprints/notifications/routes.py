from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.forms import NotificationComposeForm
from app.models import NotificationLog
from app.services.access import (
    college_has_feature,
    college_scoped_query,
    feature_required,
    get_accessible_student_ids,
    get_accessible_students,
    roles_required,
)
from app.services.helpers import flash_form_errors, log_activity
from app.services.notifications import dispatch_notification


notifications_bp = Blueprint("notifications", __name__, url_prefix="/notifications")


@notifications_bp.route("/", methods=["GET", "POST"])
@login_required
@roles_required("admin", "hod", "staff")
@feature_required("sms_notifications", "whatsapp_notifications")
def notification_center():
    form = NotificationComposeForm()
    accessible_students = get_accessible_students(current_user)
    accessible_student_ids = get_accessible_student_ids(current_user)
    form.student_id.choices = [
        (student.id, f"{student.name} ({student.register_no})") for student in accessible_students
    ]

    if form.validate_on_submit():
        student = next((item for item in accessible_students if item.id == form.student_id.data), None)
        if not student:
            flash("Select a valid student.", "danger")
            return redirect(url_for("notifications.notification_center"))
        if form.channel.data == "whatsapp" and not college_has_feature("whatsapp_notifications", current_user):
            flash("WhatsApp notifications require the Pro plan.", "warning")
            return redirect(url_for("notifications.notification_center"))

        log = dispatch_notification(
            student,
            form.channel.data,
            form.trigger_type.data,
            form.message.data.strip(),
            actor=current_user,
        )
        if log:
            log_activity(f"Queued {log.channel.upper()} notification for {student.name}", "Notifications", current_user.id)
            flash("Notification queued successfully.", "success")
            return redirect(url_for("notifications.notification_center"))
        flash("The selected notification channel is unavailable for this plan.", "warning")
    elif form.is_submitted():
        flash_form_errors(form)

    logs = (
        college_scoped_query(NotificationLog, current_user)
        .filter(NotificationLog.student_id.in_(accessible_student_ids or [0]))
        .order_by(NotificationLog.created_at.desc())
        .limit(25)
        .all()
    )

    return render_template(
        "notifications/index.html",
        form=form,
        logs=logs,
        sms_enabled=college_has_feature("sms_notifications", current_user),
        whatsapp_enabled=college_has_feature("whatsapp_notifications", current_user),
    )
