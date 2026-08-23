from flask import Blueprint, request

from .extensions import db

from .models import (
    Queue,
    Job
)
import datetime
from .auth import get_current_user


job_bp = Blueprint(
    "jobs",
    __name__
)

# =========================================================
# STEP 20
# LIST JOBS
# =========================================================

@job_bp.route(
    "/queues/<queue_id>/jobs",
    methods=["GET"]
)
def list_jobs(queue_id):

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

    # -----------------------------------------------------
    # Pagination
    # -----------------------------------------------------

    try:

        page = int(
            request.args.get(
                "page",
                1
            )
        )

        per_page = int(
            request.args.get(
                "per_page",
                10
            )
        )

    except ValueError:

        return {
            "error":
                "page and per_page must be integers"
        }, 400

    if page < 1:

        return {
            "error":
                "page must be >= 1"
        }, 400

    if per_page < 1:

        return {
            "error":
                "per_page must be >= 1"
        }, 400

    if per_page > 100:

        per_page = 100

    # -----------------------------------------------------
    # Base query
    # -----------------------------------------------------

    query = (
        Job.query
        .filter(
            Job.queue_id == queue_id
        )
    )

    # -----------------------------------------------------
    # Status filter
    # -----------------------------------------------------

    status = request.args.get(
        "status"
    )

    if status:

        query = query.filter(
            Job.status == status
        )

    # -----------------------------------------------------
    # Priority filter
    # -----------------------------------------------------

    priority = request.args.get(
        "priority"
    )

    if priority:

        try:

            priority = int(priority)

        except ValueError:

            return {
                "error":
                    "priority must be an integer"
            }, 400

        query = query.filter(
            Job.priority == priority
        )

    # -----------------------------------------------------
    # Job type filter
    # -----------------------------------------------------

    job_type = request.args.get(
        "type"
    )

    if job_type:

        query = query.filter(
            Job.job_type == job_type
        )

    # -----------------------------------------------------
    # Sort newest first
    # -----------------------------------------------------

    query = query.order_by(
        Job.created_at.desc()
    )

    # -----------------------------------------------------
    # Pagination
    # -----------------------------------------------------

    pagination = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )

    jobs = []

    for job in pagination.items:

        jobs.append({

            "id":
                job.id,

            "queue_id":
                job.queue_id,

            "type":
                job.job_type,

            "payload":
                job.payload,

            "priority":
                job.priority,

            "status":
                job.status,

            "attempts":
                job.attempts,

            "max_attempts":
                job.max_attempts,

            "run_at":
                (
                    job.run_at.isoformat()
                    if job.run_at
                    else None
                ),

            "assigned_worker_id":
                job.assigned_worker_id,

            "last_error":
                job.last_error,

            "created_at":
                job.created_at.isoformat()

        })

    return {

        "jobs":
            jobs,

        "pagination": {

            "page":
                pagination.page,

            "per_page":
                pagination.per_page,

            "total":
                pagination.total,

            "pages":
                pagination.pages,

            "has_next":
                pagination.has_next,

            "has_previous":
                pagination.has_prev
        }

    }, 200


@job_bp.route(
    "/queues/<queue_id>/jobs",
    methods=["POST"]
)
def create_job(queue_id):

    user = get_current_user()

    if not user:

        return {
            "error":
                "authentication required"
        }, 401

    data = request.get_json() or {}

    job_type = data.get("type")

    payload = data.get("payload")

    if not job_type:

        return {
            "error":
                "job type is required"
        }, 400

    if payload is None:

        return {
            "error":
                "job payload is required"
        }, 400

    queue = Queue.query.get(
        queue_id
    )

    if not queue:

        return {
            "error":
                "queue not found"
        }, 404

    if queue.paused:

        return {
            "error":
                "queue is paused"
        }, 409

    # =====================================================
    # IDEMPOTENCY
    # =====================================================

    idempotency_key = request.headers.get(
        "Idempotency-Key"
    )

    if idempotency_key:

        existing_job = (
            Job.query
            .filter_by(
                queue_id=queue.id,
                idempotency_key=idempotency_key
            )
            .first()
        )

        if existing_job:

            return {
                "message":
                    "Job already exists",

                "job_id":
                    existing_job.id,

                "status":
                    existing_job.status,

                "idempotent":
                    True
            }, 200

    # =====================================================
    # PRIORITY
    # =====================================================

    priority = data.get(
        "priority",
        0
    )

    try:

        priority = int(priority)

    except (
        TypeError,
        ValueError
    ):

        return {
            "error":
                "priority must be an integer"
        }, 400

    # =====================================================
    # RETRY SETTINGS
    # =====================================================

    max_attempts = data.get(
        "max_attempts",
        3
    )

    try:

        max_attempts = int(
            max_attempts
        )

    except (
        TypeError,
        ValueError
    ):

        return {
            "error":
                "max_attempts must be an integer"
        }, 400

    if max_attempts < 1:

        return {
            "error":
                "max_attempts must be at least 1"
        }, 400

    retry_delay = data.get(
        "retry_delay",
        2
    )

    try:

        retry_delay = int(
            retry_delay
        )

    except (
        TypeError,
        ValueError
    ):

        return {
            "error":
                "retry_delay must be an integer"
        }, 400

    retry_policy = data.get(
        "retry_policy",
        "exponential"
    )

    if retry_policy not in {
        "fixed",
        "linear",
        "exponential"
    }:

        return {
            "error":
                (
                    "retry_policy must be "
                    "fixed, linear, or exponential"
                )
        }, 400

    # =====================================================
    # STEP 17 — RUN AT
    # =====================================================

    run_at = None

    if data.get("run_at"):

        try:

            run_at = (
                datetime_from_string(
                    data["run_at"]
                )
            )

        except ValueError:

            return {
                "error":
                    (
                        "run_at must be "
                        "ISO datetime, "
                        "example: "
                        "2026-08-23T21:00:00"
                    )
            }, 400

    # =====================================================
    # CREATE JOB
    # =====================================================

    job = Job(

        queue_id=queue.id,

        job_type=job_type,

        payload=payload,

        priority=priority,

        max_attempts=max_attempts,

        retry_policy=retry_policy,

        retry_delay=retry_delay,

        run_at=run_at,

        idempotency_key=idempotency_key
    )

    db.session.add(
        job
    )

    db.session.commit()

    return {

        "message":
            "Job created successfully",

        "job_id":
            job.id,

        "status":
            job.status,

        "run_at":
            (
                job.run_at.isoformat()
                if job.run_at
                else None
            ),

        "priority":
            job.priority,

        "max_attempts":
            job.max_attempts,

        "retry_policy":
            job.retry_policy,

        "retry_delay":
            job.retry_delay,

        "idempotent":
            bool(idempotency_key)

    }, 201


# =========================================================
# DATETIME HELPER
# =========================================================

def datetime_from_string(value):

    value = value.strip()

    # Support:
    # 2026-08-23T21:00:00
    # 2026-08-23T21:00:00Z

    if value.endswith("Z"):

        value = value[:-1]

    return datetime.datetime.fromisoformat(
        value
    )