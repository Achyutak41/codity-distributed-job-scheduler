from flask import Flask

from .extensions import db
from .models import User, Organization, Membership
from .auth import auth_bp


def create_app():
    app = Flask(__name__)

    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///scheduler.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["JWT_SECRET_KEY"] = "change-this-development-secret"

    db.init_app(app)

    with app.app_context():
        db.create_all()

    app.register_blueprint(auth_bp)

    @app.route("/")
    def home():
        return {
            "message": "Distributed Job Scheduler is running"
        }

    return app