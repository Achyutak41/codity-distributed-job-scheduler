from flask import Blueprint, request

from .extensions import db
from .models import Project, Queue
from .auth import get_current_user


queue_bp = Blueprint("queues", __name__)

# =========================================================
# STEP 22
# PAUSE QUEUE
# =========================================================

@queue_bp.route(
    "/queues/<queue_id>/pause",
    methods=["POST"]
)
def pause_queue(queue_id):

    user = get_current_user()

    if not user:

        return {
            "error":
                "authentication required"
        }, 401

    queue = Queue.query.get(
        queue_id
    )

    if not queue:

        return {
            "error":
                "queue not found"
        }, 404

    queue.paused = True

    db.session.commit()

    return {

        "message":
            "Queue paused successfully",

        "queue_id":
            queue.id,

        "paused":
            queue.paused

    }, 200


# =========================================================
# RESUME QUEUE
# =========================================================

@queue_bp.route(
    "/queues/<queue_id>/resume",
    methods=["POST"]
)
def resume_queue(queue_id):

    user = get_current_user()

    if not user:

        return {
            "error":
                "authentication required"
        }, 401

    queue = Queue.query.get(
        queue_id
    )

    if not queue:

        return {
            "error":
                "queue not found"
        }, 404

    queue.paused = False

    db.session.commit()

    return {

        "message":
            "Queue resumed successfully",

        "queue_id":
            queue.id,

        "paused":
            queue.paused

    }, 200


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
    name=data["name"],
    concurrency_limit=data.get(
        "concurrency_limit",
        1
    ),
    starts_per_minute=data.get(
        "starts_per_minute",
        60
    )
)

    db.session.add(queue)
    db.session.commit()

    return {
        "message": "Queue created successfully",
        "queue_id": queue.id
    }, 201