from flask import Blueprint, request

from .extensions import db
from .models import Project, Queue
from .auth import get_current_user


queue_bp = Blueprint("queues", __name__)

@queue_bp.route(
    "/projects/<project_id>/queues",
    methods=["POST"]
)
def create_queue(project_id):

    user = get_current_user()

    if not user:
        return {
            "error": "authentication required"
        }, 401

    data = request.get_json() or {}

    name = data.get("name")

    if not name:
        return {
            "error": "queue name is required"
        }, 400

    project = Project.query.get(project_id)

    if not project:
        return {
            "error": "project not found"
        }, 404

    queue = Queue(
        project_id=project.id,
        name=name
    )

    db.session.add(queue)
    db.session.commit()

    return {
        "message": "Queue created successfully",
        "queue_id": queue.id
    }, 201