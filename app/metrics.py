from flask import Blueprint

from sqlalchemy import func

from .extensions import db

from .models import (
    Job,
    Worker,
    Queue
)

from .auth import get_current_user


metrics_bp = Blueprint(
    "metrics",
    __name__
)


@metrics_bp.route(
    "/metrics/overview",
    methods=["GET"]
)
def metrics_overview():

    user = get_current_user()

    if not user:

        return {
            "error":
                "authentication required"
        }, 401

    # =====================================================
    # JOB COUNTS
    # =====================================================

    total_jobs = (
        Job.query.count()
    )

    scheduled_jobs = (
        Job.query
        .filter_by(
            status="scheduled"
        )
        .count()
    )

    running_jobs = (
        Job.query
        .filter_by(
            status="running"
        )
        .count()
    )

    completed_jobs = (
        Job.query
        .filter_by(
            status="completed"
        )
        .count()
    )

    failed_jobs = (
        Job.query
        .filter_by(
            status="failed"
        )
        .count()
    )

    claimed_jobs = (
        Job.query
        .filter_by(
            status="claimed"
        )
        .count()
    )

    # =====================================================
    # WORKERS
    # =====================================================

    total_workers = (
        Worker.query.count()
    )

    online_workers = (
        Worker.query
        .filter_by(
            status="online"
        )
        .count()
    )

    offline_workers = (
        Worker.query
        .filter_by(
            status="offline"
        )
        .count()
    )

    # =====================================================
    # QUEUES
    # =====================================================

    total_queues = (
        Queue.query.count()
    )

    paused_queues = (
        Queue.query
        .filter_by(
            paused=True
        )
        .count()
    )

    active_queues = (
        Queue.query
        .filter_by(
            paused=False
        )
        .count()
    )

    # =====================================================
    # RESPONSE
    # =====================================================

    return {

        "jobs": {

            "total":
                total_jobs,

            "scheduled":
                scheduled_jobs,

            "claimed":
                claimed_jobs,

            "running":
                running_jobs,

            "completed":
                completed_jobs,

            "failed":
                failed_jobs
        },

        "workers": {

            "total":
                total_workers,

            "online":
                online_workers,

            "offline":
                offline_workers
        },

        "queues": {

            "total":
                total_queues,

            "active":
                active_queues,

            "paused":
                paused_queues
        }

    }, 200