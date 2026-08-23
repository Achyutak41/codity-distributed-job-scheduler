from flask import Flask
from .extensions import db
from .models import User, Organization, Membership


def create_app():
    app = Flask(__name__)

    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///scheduler.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    with app.app_context():
        db.create_all()

    @app.route("/")
    def home():
        return {
            "message": "Distributed Job Scheduler is running"
        }

    return app