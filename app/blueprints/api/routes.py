from flask import Blueprint, jsonify
from flask_login import current_user, login_required

from app.models import NotificationLog, StudentFee, TimetableEntry
from app.services.access import college_scoped_query, get_accessible_student_ids, get_accessible_students, get_current_college
from app.services.analytics import build_dashboard_payload
from app.services.serializers import (
    serialize_fee,
    serialize_notification,
    serialize_student,
    serialize_subscription,
    serialize_timetable_entry,
)


api_bp = Blueprint("api", __name__, url_prefix="/api/v1")


def _api_meta():
    college = get_current_college(current_user)
    return {
        "college": {
            "id": college.id if college else None,
            "name": college.name if college else None,
            "code": college.code if college else None,
        },
        "user": {
            "id": current_user.id,
            "name": current_user.display_name,
            "role": current_user.role,
            "email": current_user.email,
        },
    }


@api_bp.route("/me")
@login_required
def me():
    return jsonify({"meta": _api_meta()})


@api_bp.route("/dashboard")
@login_required
def dashboard():
    payload = build_dashboard_payload(current_user)
    payload["recent_activities"] = [
        {
            "action": activity.action,
            "module": activity.module,
            "created_at": activity.created_at.isoformat(),
        }
        for activity in payload["recent_activities"]
    ]
    payload["recent_notifications"] = [serialize_notification(log) for log in payload["recent_notifications"]]
    payload["top_performers"] = [
        {
            "student": serialize_student(row["student"]),
            "average_score": row["average_score"],
            "attendance": row["attendance"],
        }
        for row in payload["top_performers"]
    ]
    payload["weak_students"] = [
        {
            "student": serialize_student(row["student"]),
            "average_score": row["average_score"],
            "attendance": row["attendance"],
        }
        for row in payload["weak_students"]
    ]
    return jsonify({"meta": _api_meta(), "data": payload})


@api_bp.route("/students")
@login_required
def students():
    return jsonify(
        {
            "meta": _api_meta(),
            "data": [serialize_student(student) for student in get_accessible_students(current_user)],
        }
    )


@api_bp.route("/fees")
@login_required
def fees():
    accessible_student_ids = get_accessible_student_ids(current_user)
    fees = (
        college_scoped_query(StudentFee, current_user)
        .filter(StudentFee.student_id.in_(accessible_student_ids or [0]))
        .order_by(StudentFee.created_at.desc())
        .all()
    )
    return jsonify({"meta": _api_meta(), "data": [serialize_fee(fee) for fee in fees]})


@api_bp.route("/timetable")
@login_required
def timetable():
    accessible_student_ids = get_accessible_student_ids(current_user)
    accessible_department_ids = {student.department_id for student in get_accessible_students(current_user)}
    query = college_scoped_query(TimetableEntry, current_user)
    if current_user.role == "student" and current_user.student_profile:
        query = query.filter_by(
            department_id=current_user.student_profile.department_id,
            year=current_user.student_profile.year,
        )
    elif current_user.role == "parent":
        query = query.filter(TimetableEntry.department_id.in_(accessible_department_ids or [0]))
    elif current_user.role == "staff":
        query = query.filter((TimetableEntry.staff_id == current_user.id) | (TimetableEntry.department_id.in_(accessible_department_ids or [0])))
    elif current_user.role == "hod" and current_user.department_id:
        query = query.filter(TimetableEntry.department_id == current_user.department_id)

    entries = query.all()
    return jsonify({"meta": _api_meta(), "data": [serialize_timetable_entry(entry) for entry in entries], "student_scope": accessible_student_ids})


@api_bp.route("/notifications")
@login_required
def notifications():
    accessible_student_ids = get_accessible_student_ids(current_user)
    logs = (
        college_scoped_query(NotificationLog, current_user)
        .filter(NotificationLog.student_id.in_(accessible_student_ids or [0]))
        .order_by(NotificationLog.created_at.desc())
        .limit(50)
        .all()
    )
    return jsonify({"meta": _api_meta(), "data": [serialize_notification(log) for log in logs]})


@api_bp.route("/subscription")
@login_required
def subscription():
    college = get_current_college(current_user)
    current_subscription = college.current_subscription if college else None
    return jsonify({"meta": _api_meta(), "data": serialize_subscription(current_subscription)})
