from flask import Flask

from .extensions import db

from .models import (
    User,
    Organization,
    Membership,
    Project,
    Queue,
    Job,
    Worker,
    JobExecution,
    JobLog
)

from .auth import auth_bp
from .organizations import organization_bp
from .projects import project_bp
from .queues import queue_bp
from .jobs import job_bp


def create_app():

    app = Flask(__name__)

    app.config[
        "SQLALCHEMY_DATABASE_URI"
    ] = "sqlite:///scheduler.db"

    app.config[
        "SQLALCHEMY_TRACK_MODIFICATIONS"
    ] = False

    app.config[
        "JWT_SECRET_KEY"
    ] = "change-this-development-secret"

    db.init_app(app)

    with app.app_context():

        db.create_all()

    app.register_blueprint(
        auth_bp
    )

    app.register_blueprint(
        organization_bp
    )

    app.register_blueprint(
        project_bp
    )

    app.register_blueprint(
        queue_bp
    )

    app.register_blueprint(
        job_bp
    )

    @app.route("/")
    def home():

        return {
            "message":
                "Distributed Job Scheduler is running"
        }

    return app