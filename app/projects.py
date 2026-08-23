from flask import Blueprint, request

from .extensions import db
from .models import Organization, Project


project_bp = Blueprint("projects", __name__)
@project_bp.route(
    "/organizations/<organization_id>/projects",
    methods=["POST"]
)
def create_project(organization_id):

    data = request.get_json()

    name = data.get("name")

    if not name:
        return {
            "error": "project name is required"
        }, 400

    organization = Organization.query.get(organization_id)

    if not organization:
        return {
            "error": "organization not found"
        }, 404

    project = Project(
        organization_id=organization.id,
        name=name
    )

    db.session.add(project)
    db.session.commit()

    return {
        "message": "Project created successfully",
        "project_id": project.id
    }, 201