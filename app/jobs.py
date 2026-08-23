from flask import Blueprint, request

from .extensions import db
from .models import Queue, Job
from .auth import get_current_user


job_bp = Blueprint("jobs", __name__)

@job_bp.route(
    "/queues/<queue_id>/jobs",
    methods=["POST"]
)
def create_job(queue_id):

    user = get_current_user()

    if not user:
        return {
            "error": "authentication required"
        }, 401

    data = request.get_json() or {}

    job_type = data.get("type")
    payload = data.get("payload")

    if not job_type:
        return {
            "error": "job type is required"
        }, 400

    if payload is None:
        return {
            "error": "job payload is required"
        }, 400

    queue = Queue.query.get(queue_id)

    if not queue:
        return {
            "error": "queue not found"
        }, 404

    if queue.paused:
        return {
            "error": "queue is paused"
        }, 409

    job = Job(
        queue_id=queue.id,
        job_type=job_type,
        payload=payload,
        priority=data.get("priority", 0)
    )

    db.session.add(job)
    db.session.commit()

    return {
        "message": "Job created successfully",
        "job_id": job.id,
        "status": job.status
    }, 201