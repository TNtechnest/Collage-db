from flask import Blueprint, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.services.access import employee_required, get_current_college, user_home_endpoint
from app.services.analytics import build_dashboard_payload


main_bp = Blueprint("main", __name__)


@main_bp.route("/")
@login_required
@employee_required
def dashboard():
    if current_user.role in {"student", "parent"}:
        return redirect(url_for(user_home_endpoint(current_user)))

    current_college = get_current_college(current_user)
    subscription = current_college.current_subscription if current_college else None
    dashboard_payload = build_dashboard_payload(current_user)
    return render_template(
        "dashboard/index.html",
        current_college=current_college,
        subscription=subscription,
        **dashboard_payload,
    )
