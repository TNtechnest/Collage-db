from collections import defaultdict
from datetime import date

from app.models import ActivityLog, Attendance, Department, NotificationLog, ResultSummary, StudentFee
from app.services.access import (
    college_scoped_query,
    get_accessible_students,
    get_college_departments,
)


def _month_key(value):
    return value.strftime("%Y-%m") if value else ""


def build_dashboard_payload(user):
    students = get_accessible_students(user)
    student_ids = [student.id for student in students] or [0]
    departments = get_college_departments(user)
    department_map = {department.id: department.name for department in departments}

    attendance_records = (
        college_scoped_query(Attendance, user)
        .filter(Attendance.student_id.in_(student_ids))
        .order_by(Attendance.attendance_date)
        .all()
    )
    result_summaries = (
        college_scoped_query(ResultSummary, user)
        .filter(ResultSummary.student_id.in_(student_ids))
        .order_by(ResultSummary.created_at)
        .all()
    )
    fee_records = (
        college_scoped_query(StudentFee, user)
        .filter(StudentFee.student_id.in_(student_ids))
        .all()
    )
    recent_activities = (
        college_scoped_query(ActivityLog, user)
        .order_by(ActivityLog.created_at.desc())
        .limit(8)
        .all()
    )
    recent_notifications = (
        college_scoped_query(NotificationLog, user)
        .filter(NotificationLog.student_id.in_(student_ids))
        .order_by(NotificationLog.created_at.desc())
        .limit(6)
        .all()
    )

    total_attendance = len(attendance_records)
    present_count = sum(1 for record in attendance_records if record.status == "Present")
    attendance_percentage = round((present_count / total_attendance) * 100, 2) if total_attendance else 0

    attendance_by_month = defaultdict(lambda: {"present": 0, "total": 0})
    for record in attendance_records:
        key = _month_key(record.attendance_date)
        attendance_by_month[key]["total"] += 1
        if record.status == "Present":
            attendance_by_month[key]["present"] += 1

    monthly_labels = []
    monthly_attendance_values = []
    for key in sorted(attendance_by_month):
        monthly_labels.append(date.fromisoformat(f"{key}-01").strftime("%b"))
        month_data = attendance_by_month[key]
        monthly_attendance_values.append(
            round((month_data["present"] / month_data["total"]) * 100, 2) if month_data["total"] else 0
        )

    distribution_counter = defaultdict(int)
    for student in students:
        distribution_counter[student.department.name if student.department else "Unassigned"] += 1

    distribution_labels = list(distribution_counter.keys())
    distribution_values = list(distribution_counter.values())

    department_scores = defaultdict(list)
    monthly_scores = defaultdict(list)
    student_scores = defaultdict(list)
    for summary in result_summaries:
        if summary.student.department_id in department_map:
            department_scores[department_map[summary.student.department_id]].append(summary.percentage)
        monthly_scores[_month_key(summary.created_at.date() if summary.created_at else date.today())].append(summary.percentage)
        student_scores[summary.student_id].append(summary.percentage)

    performance_labels = list(department_scores.keys())
    performance_values = [
        round(sum(scores) / len(scores), 2) if scores else 0 for scores in department_scores.values()
    ]

    monthly_performance_labels = []
    monthly_performance_values = []
    for key in sorted(monthly_scores):
        monthly_performance_labels.append(date.fromisoformat(f"{key}-01").strftime("%b"))
        scores = monthly_scores[key]
        monthly_performance_values.append(round(sum(scores) / len(scores), 2) if scores else 0)

    attendance_by_student = defaultdict(list)
    for record in attendance_records:
        attendance_by_student[record.student_id].append(record.status)

    top_performers = []
    weak_students = []
    for student in students:
        result_scores = student_scores.get(student.id, [])
        avg_score = round(sum(result_scores) / len(result_scores), 2) if result_scores else 0
        attendance_statuses = attendance_by_student.get(student.id, [])
        student_attendance = round(
            (attendance_statuses.count("Present") / len(attendance_statuses)) * 100,
            2,
        ) if attendance_statuses else 0
        row = {
            "student": student,
            "average_score": avg_score,
            "attendance": student_attendance,
        }
        if result_scores:
            top_performers.append(row)
        if student_attendance < 75 or (result_scores and avg_score < 60):
            weak_students.append(row)

    top_performers = sorted(top_performers, key=lambda item: item["average_score"], reverse=True)[:5]
    weak_students = sorted(weak_students, key=lambda item: (item["average_score"], item["attendance"]))[:5]

    total_fees_collected = round(sum(fee.amount_paid for fee in fee_records), 2)
    pending_dues = round(sum(max(fee.total_amount - fee.amount_paid, 0) for fee in fee_records), 2)

    return {
        "total_students": len(students),
        "attendance_percentage": attendance_percentage,
        "total_departments": len(departments),
        "total_results": len(result_summaries),
        "total_fees_collected": total_fees_collected,
        "pending_dues": pending_dues,
        "monthly_labels": monthly_labels,
        "monthly_attendance_values": monthly_attendance_values,
        "distribution_labels": distribution_labels,
        "distribution_values": distribution_values,
        "performance_labels": performance_labels,
        "performance_values": performance_values,
        "monthly_performance_labels": monthly_performance_labels,
        "monthly_performance_values": monthly_performance_values,
        "top_performers": top_performers,
        "weak_students": weak_students,
        "recent_activities": recent_activities,
        "recent_notifications": recent_notifications,
    }
