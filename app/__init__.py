import os

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from app.config import Config
from app.extensions import csrf, db, login_manager
from app.models import Setting, User
from app.services.access import ROLE_LABELS, get_current_college, get_plan_features


def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    from app.blueprints.auth.routes import auth_bp
    from app.blueprints.main.routes import main_bp
    from app.blueprints.students.routes import students_bp
    from app.blueprints.attendance.routes import attendance_bp
    from app.blueprints.results.routes import results_bp
    from app.blueprints.reports.routes import reports_bp
    from app.blueprints.settings.routes import settings_bp
    from app.blueprints.staff.routes import staff_bp
    from app.blueprints.subjects.routes import subjects_bp
    from app.blueprints.fees.routes import fees_bp
    from app.blueprints.timetable.routes import timetable_bp
    from app.blueprints.notifications.routes import notifications_bp
    from app.blueprints.portal.routes import portal_bp
    from app.blueprints.files.routes import files_bp
    from app.blueprints.saas.routes import saas_bp
    from app.blueprints.api.routes import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(students_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(results_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(staff_bp)
    app.register_blueprint(subjects_bp)
    app.register_blueprint(fees_bp)
    app.register_blueprint(timetable_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(portal_bp)
    app.register_blueprint(files_bp)
    app.register_blueprint(saas_bp)
    app.register_blueprint(api_bp)

    @app.context_processor
    def inject_global_template_data():
        college = get_current_college()
        college_name_setting = Setting.query.filter_by(key="college_name").first()
        plan_features = get_plan_features()
        return {
            "college_name": college.name if college else (college_name_setting.value if college_name_setting else "College Dashboard"),
            "active_college": college,
            "active_plan": college.active_plan if college else None,
            "plan_features": plan_features,
            "role_labels": ROLE_LABELS,
        }

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    with app.app_context():
        from app.services.schema import sync_schema
        from app.services.seed import seed_initial_data

        sync_schema()
        seed_initial_data()

    return app
