from flask import Blueprint, request

from .extensions import db
from .models import Organization, Membership
from .auth import get_current_user


organization_bp = Blueprint("organizations", __name__)


@organization_bp.route("/organizations", methods=["POST"])
def create_organization():
    user = get_current_user()

    if not user:
        return {
            "error": "authentication required"
        }, 401

    data = request.get_json() or {}

    name = data.get("name")

    if not name:
        return {
            "error": "organization name is required"
        }, 400

    existing_organization = Organization.query.filter_by(
        name=name
    ).first()

    if existing_organization:
        return {
            "error": "organization already exists"
        }, 409

    organization = Organization(
        name=name
    )

    db.session.add(organization)
    db.session.flush()

    membership = Membership(
        user_id=user.id,
        organization_id=organization.id
    )

    db.session.add(membership)
    db.session.commit()

    return {
        "message": "Organization created successfully",
        "organization_id": organization.id
    }, 201