from datetime import datetime
from uuid import uuid4

from flask import current_app

from app.extensions import db
from app.models import NotificationLog
from app.services.access import college_has_feature, get_current_college


CHANNEL_FEATURES = {
    "sms": "sms_notifications",
    "whatsapp": "whatsapp_notifications",
}


def default_recipient_for_student(student):
    if student.parents:
        primary_parent = student.parents[0]
        if primary_parent.phone:
            return primary_parent.phone
    return student.phone or student.register_no


def dispatch_notification(student, channel, trigger_type, message, actor=None, recipient=None):
    feature_key = CHANNEL_FEATURES.get(channel)
    if feature_key and not college_has_feature(feature_key, actor):
        return None

    college = get_current_college(actor or student.portal_user)
    if not college:
        return None

    log = NotificationLog(
        college_id=college.id,
        student_id=student.id if student else None,
        triggered_by_user_id=actor.id if actor else None,
        channel=channel,
        recipient=recipient or default_recipient_for_student(student),
        message=message,
        trigger_type=trigger_type,
        status="queued",
        provider=current_app.config.get(f"{channel.upper()}_PROVIDER_NAME", f"{channel}-stub"),
        external_reference=f"{channel}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:8]}",
    )
    db.session.add(log)
    db.session.commit()
    return log


def queue_attendance_notification(student, attendance_record, actor=None):
    message = (
        f"Attendance update: {student.name} was marked {attendance_record.status} "
        f"on {attendance_record.attendance_date.strftime('%d %b %Y')}."
    )
    return dispatch_notification(student, "sms", "attendance", message, actor=actor)


def queue_result_notification(student, result_summary, actor=None):
    message = (
        f"Result announced for {result_summary.exam_name}: "
        f"{student.name} scored {result_summary.percentage}% ({result_summary.result_status})."
    )
    return dispatch_notification(student, "sms", "results", message, actor=actor)
