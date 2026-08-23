import datetime
import jwt

from flask import Blueprint, request, current_app
from werkzeug.security import generate_password_hash, check_password_hash

from .extensions import db
from .models import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/auth/register", methods=["POST"])
def register():
    data = request.get_json()

    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return {
            "error": "username and password are required"
        }, 400

    existing_user = User.query.filter_by(
        username=username
    ).first()

    if existing_user:
        return {
            "error": "username already exists"
        }, 409

    password_hash = generate_password_hash(password)

    user = User(
    username=username,
    password=password_hash
)

    db.session.add(user)
    db.session.commit()

    return {
        "message": "User registered successfully",
        "user_id": user.id
    }, 201


@auth_bp.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json()

    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return {
            "error": "username and password are required"
        }, 400

    user = User.query.filter_by(
        username=username
    ).first()

    if not user:
        return {
            "error": "invalid username or password"
        }, 401

    if not check_password_hash(user.password, password):
        return {
            "error": "invalid username or password"
        }, 401

    token = jwt.encode(
    {
        "user_id": user.id,
        "exp": datetime.datetime.now(datetime.timezone.utc)
        + datetime.timedelta(hours=1)
    },
    current_app.config["JWT_SECRET_KEY"],
    algorithm="HS256"
    )
    
    return {
    "message": "Login successful",
    "access_token": token
}, 200