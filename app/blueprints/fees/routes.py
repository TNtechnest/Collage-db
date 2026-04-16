from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.forms import FeeCategoryForm, FeePaymentForm, StudentFeeForm
from app.models import FeeCategory, FeePayment, StudentFee
from app.services.access import (
    college_scoped_query,
    employee_required,
    feature_required,
    get_accessible_student_ids,
    get_accessible_students,
    get_current_college,
)
from app.services.helpers import flash_form_errors, log_activity


fees_bp = Blueprint("fees", __name__, url_prefix="/fees")


def _hydrate_fee_forms(category_form, fee_form):
    accessible_students = get_accessible_students(current_user)
    fee_form.student_id.choices = [
        (student.id, f"{student.name} ({student.register_no})") for student in accessible_students
    ]
    fee_form.fee_category_id.choices = [
        (category.id, f"{category.name} - {category.default_amount:.2f}")
        for category in college_scoped_query(FeeCategory, current_user).order_by(FeeCategory.name).all()
    ]
    return accessible_students


def _sync_fee_status(student_fee):
    student_fee.status = "paid" if student_fee.amount_paid >= student_fee.total_amount else "pending"


@fees_bp.route("/", methods=["GET", "POST"])
@login_required
@employee_required
@feature_required("fee_management")
def manage_fees():
    category_form = FeeCategoryForm(prefix="category")
    fee_form = StudentFeeForm(prefix="fee")
    accessible_students = _hydrate_fee_forms(category_form, fee_form)
    accessible_student_ids = get_accessible_student_ids(current_user)
    current_college = get_current_college(current_user)

    if category_form.submit.data:
        if current_user.role != "admin":
            flash("Only administrators can create fee categories.", "danger")
            return redirect(url_for("fees.manage_fees"))
        if category_form.validate_on_submit():
            category = FeeCategory(
                college_id=current_college.id if current_college else None,
                name=category_form.name.data.strip(),
                description=(category_form.description.data or "").strip() or None,
                default_amount=category_form.default_amount.data,
            )
            db.session.add(category)
            db.session.commit()
            log_activity(f"Created fee category {category.name}", "Fees", current_user.id)
            flash("Fee category saved successfully.", "success")
            return redirect(url_for("fees.manage_fees"))
        flash_form_errors(category_form)

    if fee_form.submit.data:
        if current_user.role not in {"admin", "hod"}:
            flash("Only admins and HODs can assign fee records.", "danger")
            return redirect(url_for("fees.manage_fees"))
        if fee_form.validate_on_submit():
            category_ids = [category.id for category in college_scoped_query(FeeCategory, current_user).all()]
            if fee_form.student_id.data not in (accessible_student_ids or []) or fee_form.fee_category_id.data not in category_ids:
                flash("Select valid student and fee category records.", "danger")
                return redirect(url_for("fees.manage_fees"))
            student_fee = StudentFee(
                college_id=current_college.id if current_college else None,
                student_id=fee_form.student_id.data,
                fee_category_id=fee_form.fee_category_id.data,
                total_amount=fee_form.total_amount.data,
                due_date=fee_form.due_date.data,
                amount_paid=0,
                created_by_user_id=current_user.id,
            )
            _sync_fee_status(student_fee)
            db.session.add(student_fee)
            db.session.commit()
            log_activity(f"Assigned fee record #{student_fee.id}", "Fees", current_user.id)
            flash("Student fee assigned successfully.", "success")
            return redirect(url_for("fees.manage_fees"))
        flash_form_errors(fee_form)

    fees = (
        college_scoped_query(StudentFee, current_user)
        .filter(StudentFee.student_id.in_(accessible_student_ids or [0]))
        .order_by(StudentFee.due_date.asc(), StudentFee.created_at.desc())
        .all()
    )
    payments = (
        college_scoped_query(FeePayment, current_user)
        .join(StudentFee)
        .filter(StudentFee.student_id.in_(accessible_student_ids or [0]))
        .order_by(FeePayment.payment_date.desc(), FeePayment.created_at.desc())
        .limit(12)
        .all()
    )
    categories = college_scoped_query(FeeCategory, current_user).order_by(FeeCategory.name).all()

    total_collected = round(sum(fee.amount_paid for fee in fees), 2)
    pending_dues = round(sum(fee.due_amount for fee in fees), 2)
    pending_count = sum(1 for fee in fees if fee.status != "paid")

    return render_template(
        "fees/index.html",
        category_form=category_form,
        fee_form=fee_form,
        categories=categories,
        fees=fees,
        payments=payments,
        total_collected=total_collected,
        pending_dues=pending_dues,
        pending_count=pending_count,
        accessible_students=accessible_students,
        today=date.today(),
    )


@fees_bp.route("/<int:fee_id>/pay", methods=["GET", "POST"])
@login_required
@feature_required("fee_management")
def record_payment(fee_id):
    accessible_student_ids = get_accessible_student_ids(current_user)
    student_fee = (
        college_scoped_query(StudentFee, current_user)
        .filter(StudentFee.id == fee_id, StudentFee.student_id.in_(accessible_student_ids or [0]))
        .first_or_404()
    )

    if current_user.role not in {"admin", "hod"}:
        flash("Only admins and HODs can record fee payments.", "danger")
        return redirect(url_for("fees.manage_fees"))

    form = FeePaymentForm()
    if request.method == "GET":
        form.payment_date.data = date.today()

    if form.validate_on_submit():
        payment = FeePayment(
            college_id=student_fee.college_id,
            student_fee_id=student_fee.id,
            amount=form.amount.data,
            payment_date=form.payment_date.data,
            payment_method=form.payment_method.data,
            reference=(form.reference.data or "").strip() or None,
        )
        student_fee.amount_paid = round(student_fee.amount_paid + form.amount.data, 2)
        _sync_fee_status(student_fee)
        db.session.add(payment)
        db.session.commit()
        log_activity(f"Recorded payment for fee #{student_fee.id}", "Fees", current_user.id)
        flash("Payment recorded successfully.", "success")
        return redirect(url_for("fees.manage_fees"))
    if request.method == "POST":
        flash_form_errors(form)

    return render_template("fees/payment.html", form=form, student_fee=student_fee)
