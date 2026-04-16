from flask import flash

from app.extensions import db
from app.models import ActivityLog
from app.services.access import get_current_college


def log_activity(action, module, user=None, user_id=None, college_id=None):
    user_object = user if hasattr(user, "id") else None
    actor_id = user_id or (user if isinstance(user, int) else None) or (user_object.id if user_object else None)
    scoped_college_id = college_id or (user_object.college_id if user_object else None)
    if scoped_college_id is None:
        college = get_current_college(user_object)
        scoped_college_id = college.id if college else None
    activity = ActivityLog(action=action, module=module, user_id=actor_id, college_id=scoped_college_id)
    db.session.add(activity)
    db.session.commit()


def flash_form_errors(form):
    for field, errors in form.errors.items():
        for error in errors:
            flash(f"{getattr(form, field).label.text}: {error}", "danger")
