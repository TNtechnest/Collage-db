from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_

from app.extensions import db
from app.forms import TimeSlotForm, TimetableEntryForm
from app.models import TimeSlot, TimetableEntry
from app.services.access import (
    college_scoped_query,
    employee_required,
    feature_required,
    get_accessible_subjects,
    get_college_departments,
    get_college_users,
    get_current_college,
)
from app.services.helpers import flash_form_errors, log_activity


timetable_bp = Blueprint("timetable", __name__, url_prefix="/timetable")


def _hydrate_timetable_forms(slot_form, entry_form):
    departments = get_college_departments(current_user)
    subjects = get_accessible_subjects(current_user)
    staff_members = get_college_users(current_user, roles=["staff", "hod"])
    time_slots = college_scoped_query(TimeSlot, current_user).order_by(TimeSlot.weekday, TimeSlot.start_time).all()

    entry_form.department_id.choices = [(department.id, department.name) for department in departments]
    entry_form.subject_id.choices = [(subject.id, f"{subject.name} ({subject.code})") for subject in subjects]
    entry_form.staff_id.choices = [(staff.id, staff.display_name) for staff in staff_members]
    entry_form.time_slot_id.choices = [
        (slot.id, f"{slot.weekday} | {slot.label} | {slot.start_time.strftime('%H:%M')} - {slot.end_time.strftime('%H:%M')}")
        for slot in time_slots
    ]
    return departments, subjects, staff_members, time_slots


@timetable_bp.route("/", methods=["GET", "POST"])
@login_required
@employee_required
@feature_required("timetable")
def manage_timetable():
    slot_form = TimeSlotForm(prefix="slot")
    entry_form = TimetableEntryForm(prefix="entry")
    departments, subjects, staff_members, time_slots = _hydrate_timetable_forms(slot_form, entry_form)
    current_college = get_current_college(current_user)

    if slot_form.submit.data:
        if current_user.role not in {"admin", "hod"}:
            flash("Only admins and HODs can create time slots.", "danger")
            return redirect(url_for("timetable.manage_timetable"))
        if slot_form.validate_on_submit():
            slot = TimeSlot(
                college_id=current_college.id if current_college else None,
                label=slot_form.label.data.strip(),
                weekday=slot_form.weekday.data,
                start_time=slot_form.start_time.data,
                end_time=slot_form.end_time.data,
            )
            db.session.add(slot)
            db.session.commit()
            log_activity(f"Created timetable slot {slot.label}", "Timetable", current_user.id)
            flash("Time slot added successfully.", "success")
            return redirect(url_for("timetable.manage_timetable"))
        flash_form_errors(slot_form)

    if entry_form.submit.data:
        if current_user.role not in {"admin", "hod"}:
            flash("Only admins and HODs can assign timetable entries.", "danger")
            return redirect(url_for("timetable.manage_timetable"))
        if entry_form.validate_on_submit():
            department_ids = [department.id for department in departments]
            subject_ids = [subject.id for subject in subjects]
            staff_ids = [staff.id for staff in staff_members]
            slot_ids = [slot.id for slot in time_slots]
            if (
                entry_form.department_id.data not in department_ids
                or entry_form.subject_id.data not in subject_ids
                or entry_form.staff_id.data not in staff_ids
                or entry_form.time_slot_id.data not in slot_ids
            ):
                flash("Select valid timetable references for this tenant scope.", "danger")
                return redirect(url_for("timetable.manage_timetable"))
            entry = TimetableEntry(
                college_id=current_college.id if current_college else None,
                department_id=entry_form.department_id.data,
                year=entry_form.year.data,
                subject_id=entry_form.subject_id.data,
                staff_id=entry_form.staff_id.data,
                time_slot_id=entry_form.time_slot_id.data,
                room=entry_form.room.data.strip(),
            )
            db.session.add(entry)
            db.session.commit()
            log_activity(f"Created timetable entry for room {entry.room}", "Timetable", current_user.id)
            flash("Timetable entry saved successfully.", "success")
            return redirect(url_for("timetable.manage_timetable"))
        flash_form_errors(entry_form)

    entries_query = college_scoped_query(TimetableEntry, current_user)
    if current_user.role == "hod" and current_user.department_id:
        entries_query = entries_query.filter(TimetableEntry.department_id == current_user.department_id)
    elif current_user.role == "staff":
        department_ids = [department.id for department in departments]
        entries_query = entries_query.filter(
            or_(TimetableEntry.staff_id == current_user.id, TimetableEntry.department_id.in_(department_ids or [0]))
        )

    entries = entries_query.join(TimeSlot).order_by(TimeSlot.weekday, TimeSlot.start_time, TimetableEntry.room).all()
    personal_schedule = (
        college_scoped_query(TimetableEntry, current_user)
        .filter(TimetableEntry.staff_id == current_user.id)
        .join(TimeSlot)
        .order_by(TimeSlot.weekday, TimeSlot.start_time)
        .all()
    ) if current_user.role in {"staff", "hod"} else []

    return render_template(
        "timetable/index.html",
        slot_form=slot_form,
        entry_form=entry_form,
        departments=departments,
        subjects=subjects,
        staff_members=staff_members,
        time_slots=time_slots,
        entries=entries,
        personal_schedule=personal_schedule,
    )
