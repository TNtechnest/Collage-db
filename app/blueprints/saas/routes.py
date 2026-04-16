from datetime import date

from flask import Blueprint, current_app, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.forms import SubscriptionForm
from app.models import CollegeSubscription, Student, SubscriptionPlan, User
from app.services.access import admin_required, college_scoped_query, get_current_college
from app.services.helpers import log_activity
from app.services.serializers import serialize_subscription


saas_bp = Blueprint("saas", __name__, url_prefix="/saas")


@saas_bp.route("/", methods=["GET", "POST"])
@login_required
@admin_required
def tenant_center():
    form = SubscriptionForm()
    college = get_current_college(current_user)
    plans = SubscriptionPlan.query.order_by(SubscriptionPlan.monthly_price).all()
    current_subscription = college.current_subscription if college else None
    history = (
        CollegeSubscription.query.filter_by(college_id=college.id).order_by(CollegeSubscription.created_at.desc()).all()
        if college else []
    )
    form.plan_id.choices = [(plan.id, f"{plan.name} - {plan.monthly_price:.0f}/month") for plan in plans]

    if current_subscription and not form.is_submitted():
        form.plan_id.data = current_subscription.plan_id
        form.status.data = current_subscription.status

    if form.validate_on_submit():
        subscription = CollegeSubscription(
            college_id=college.id if college else None,
            plan_id=form.plan_id.data,
            status=form.status.data,
            start_date=date.today(),
            payment_reference=f"manual-{date.today().isoformat()}",
        )
        db.session.add(subscription)
        db.session.commit()
        log_activity("Updated tenant subscription", "Subscription", current_user.id)
        flash("Subscription updated successfully.", "success")
        return redirect(url_for("saas.tenant_center"))

    tenant_metrics = {
        "users": college_scoped_query(User, current_user).count(),
        "students": college_scoped_query(Student, current_user).count(),
    }
    razorpay_payload = {
        "key_id": current_app.config.get("RAZORPAY_KEY_ID") or "rzp_test_placeholder",
        "tenant_code": college.code if college else "NA",
        "plan_code": current_subscription.plan.code if current_subscription and current_subscription.plan else "basic",
        "subscription_reference": current_subscription.payment_reference if current_subscription else None,
    }

    return render_template(
        "saas/index.html",
        form=form,
        college=college,
        plans=plans,
        current_subscription=current_subscription,
        history=history,
        tenant_metrics=tenant_metrics,
        razorpay_payload=razorpay_payload,
        subscription_json=serialize_subscription(current_subscription),
    )
