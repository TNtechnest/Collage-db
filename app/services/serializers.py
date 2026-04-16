def serialize_student(student):
    return {
        "id": student.id,
        "name": student.name,
        "register_no": student.register_no,
        "phone": student.phone,
        "year": student.year,
        "department": student.department.name if student.department else None,
        "attendance_percentage": student.attendance_percentage,
        "total_fees_paid": student.total_fees_paid,
        "total_fees_due": student.total_fees_due,
    }


def serialize_fee(student_fee):
    return {
        "id": student_fee.id,
        "student": student_fee.student.name if student_fee.student else None,
        "category": student_fee.category.name if student_fee.category else None,
        "total_amount": student_fee.total_amount,
        "amount_paid": student_fee.amount_paid,
        "due_amount": student_fee.due_amount,
        "status": student_fee.status,
        "due_date": student_fee.due_date.isoformat() if student_fee.due_date else None,
        "payments": [
            {
                "amount": payment.amount,
                "payment_date": payment.payment_date.isoformat(),
                "payment_method": payment.payment_method,
                "reference": payment.reference,
            }
            for payment in student_fee.payments
        ],
    }


def serialize_timetable_entry(entry):
    return {
        "id": entry.id,
        "department": entry.department.name if entry.department else None,
        "year": entry.year,
        "subject": entry.subject.name if entry.subject else None,
        "staff": entry.staff_member.display_name if entry.staff_member else None,
        "weekday": entry.time_slot.weekday if entry.time_slot else None,
        "slot": entry.time_slot.label if entry.time_slot else None,
        "start_time": entry.time_slot.start_time.strftime("%H:%M") if entry.time_slot else None,
        "end_time": entry.time_slot.end_time.strftime("%H:%M") if entry.time_slot else None,
        "room": entry.room,
    }


def serialize_notification(log):
    return {
        "id": log.id,
        "student": log.student.name if log.student else None,
        "channel": log.channel,
        "recipient": log.recipient,
        "trigger_type": log.trigger_type,
        "status": log.status,
        "provider": log.provider,
        "external_reference": log.external_reference,
        "created_at": log.created_at.isoformat(),
    }


def serialize_subscription(subscription):
    plan = subscription.plan if subscription else None
    return {
        "status": subscription.status if subscription else None,
        "start_date": subscription.start_date.isoformat() if subscription and subscription.start_date else None,
        "end_date": subscription.end_date.isoformat() if subscription and subscription.end_date else None,
        "payment_reference": subscription.payment_reference if subscription else None,
        "razorpay_plan_id": subscription.razorpay_plan_id if subscription else None,
        "razorpay_subscription_id": subscription.razorpay_subscription_id if subscription else None,
        "plan": {
            "name": plan.name,
            "code": plan.code,
            "monthly_price": plan.monthly_price,
            "features": plan.features,
        } if plan else None,
    }
