# College Management Dashboard SaaS

A production-structured Flask web application for managing student records, attendance, results, reports, and institution settings with a modern Bootstrap 5 dashboard UI.

## Features

- Secure authentication with Flask-Login
- Role-aware users (`admin`, `staff`)
- Staff management with department, role, and subject assignment
- Subject management with admin CRUD and staff-scoped visibility
- Dashboard analytics with Chart.js
- Student CRUD with search, filters, validation, and pagination
- Attendance marking with date-wise records and auto percentage calculation
- Internal marks entry with automatic result summary calculation
- University results upload through Excel (`.xlsx`)
- Excel and PDF report exports
- College settings and department management
- Mobile-responsive sidebar and table layouts
- Seeded dummy data for quick preview

## Project Structure

```text
college-dashboard-saas/
├── app/
│   ├── blueprints/
│   ├── services/
│   ├── static/
│   ├── templates/
│   ├── __init__.py
│   ├── config.py
│   ├── extensions.py
│   ├── forms.py
│   └── models.py
├── instance/
├── requirements.txt
└── run.py
```

## Setup

1. Create a virtual environment: `python -m venv .venv`
2. Activate it: `.\.venv\Scripts\Activate.ps1`
3. Install dependencies: `pip install -r requirements.txt`
4. Run the app: `python run.py`
5. Open `http://127.0.0.1:5000`

## Default Accounts

- Admin: `admin` / `admin123`
- Staff: `staff` / `staff123`
- ECE Staff: `faculty.ece@college.local` / `faculty123`

## University Result Upload Format

Columns in order:
1. Register No
2. Total Marks
3. Percentage
4. Result Status

## Notes

- SQLite is the default database and can be swapped for PostgreSQL with `DATABASE_URL`.
- Seed data is created automatically on first launch.
- For production, replace `SECRET_KEY`, move to PostgreSQL, and serve with Gunicorn or Waitress.
