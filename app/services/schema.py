from sqlalchemy import inspect, text

from app.extensions import db


COLUMN_PATCHES = {
    "users": {
        "full_name": "ALTER TABLE users ADD COLUMN full_name VARCHAR(120)",
        "department_id": "ALTER TABLE users ADD COLUMN department_id INTEGER",
        "college_id": "ALTER TABLE users ADD COLUMN college_id INTEGER",
        "phone": "ALTER TABLE users ADD COLUMN phone VARCHAR(30)",
    },
    "departments": {
        "college_id": "ALTER TABLE departments ADD COLUMN college_id INTEGER",
    },
    "students": {
        "college_id": "ALTER TABLE students ADD COLUMN college_id INTEGER",
        "user_id": "ALTER TABLE students ADD COLUMN user_id INTEGER",
        "phone": "ALTER TABLE students ADD COLUMN phone VARCHAR(30)",
    },
    "subjects": {
        "college_id": "ALTER TABLE subjects ADD COLUMN college_id INTEGER",
    },
    "attendance": {
        "college_id": "ALTER TABLE attendance ADD COLUMN college_id INTEGER",
    },
    "marks": {
        "college_id": "ALTER TABLE marks ADD COLUMN college_id INTEGER",
    },
    "results_summary": {
        "college_id": "ALTER TABLE results_summary ADD COLUMN college_id INTEGER",
    },
    "activity_logs": {
        "college_id": "ALTER TABLE activity_logs ADD COLUMN college_id INTEGER",
    },
}


def sync_schema():
    db.create_all()
    inspector = inspect(db.engine)
    table_names = set(inspector.get_table_names())

    for table_name, patches in COLUMN_PATCHES.items():
        if table_name not in table_names:
            continue
        existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
        for column_name, statement in patches.items():
            if column_name not in existing_columns:
                db.session.execute(text(statement))
                db.session.commit()

    db.create_all()
