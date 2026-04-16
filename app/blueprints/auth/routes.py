from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import or_

from app.forms import LoginForm
from app.models import User
from app.services.access import user_home_endpoint
from app.services.helpers import flash_form_errors, log_activity


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for(user_home_endpoint(current_user)))

    form = LoginForm()
    if form.validate_on_submit():
        identifier = form.username.data.strip().lower()
        user = User.query.filter(
            or_(User.username == identifier, User.email == identifier)
        ).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            log_activity("Logged into dashboard", "Authentication", user.id)
            flash("Welcome back. You have signed in successfully.", "success")
            next_url = request.args.get("next")
            return redirect(next_url or url_for(user_home_endpoint(user)))
        flash("Invalid username or password.", "danger")
    elif request.method == "POST":
        flash_form_errors(form)

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    log_activity("Logged out", "Authentication", current_user.id)
    logout_user()
    flash("You have been signed out.", "info")
    return redirect(url_for("auth.login"))
