from flask import Blueprint, request

from .extensions import db

from .models import (
    Queue,
    Job
)

from .auth import get_current_user


job_bp = Blueprint(
    "jobs",
    __name__
)


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
    # STEP 16: IDEMPOTENCY KEY
    # =====================================================

    idempotency_key = request.headers.get(
        "Idempotency-Key"
    )

    # -----------------------------------------------------
    # If an idempotency key was supplied, check whether
    # this job already exists.
    # -----------------------------------------------------

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
    # VALIDATE MAX ATTEMPTS
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

    # =====================================================
    # VALIDATE RETRY DELAY
    # =====================================================

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

    if retry_delay < 0:

        return {
            "error":
                "retry_delay cannot be negative"
        }, 400

    # =====================================================
    # VALIDATE RETRY POLICY
    # =====================================================

    retry_policy = data.get(
        "retry_policy",
        "exponential"
    )

    allowed_policies = {
        "fixed",
        "linear",
        "exponential"
    }

    if retry_policy not in allowed_policies:

        return {
            "error":
                (
                    "retry_policy must be "
                    "fixed, linear, or exponential"
                )
        }, 400

    # =====================================================
    # VALIDATE PRIORITY
    # =====================================================

    priority = data.get(
        "priority",
        0
    )

    try:

        priority = int(
            priority
        )

    except (
        TypeError,
        ValueError
    ):

        return {
            "error":
                "priority must be an integer"
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

        "max_attempts":
            job.max_attempts,

        "retry_policy":
            job.retry_policy,

        "retry_delay":
            job.retry_delay,

        "idempotent":
            bool(idempotency_key)

    }, 201