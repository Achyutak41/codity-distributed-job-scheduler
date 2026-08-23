import time
import datetime

from flask import current_app

from .extensions import db

from .models import (
    Job,
    Worker,
    JobExecution,
    JobLog
)


def claim_next_job(worker_id):
    job = (
        Job.query
        .filter_by(status="scheduled")
        .order_by(
            Job.priority.desc(),
            Job.created_at.asc()
        )
        .first()
    )

    if job is None:
        return None

    updated = (
        db.session.query(Job)
        .filter(
            Job.id == job.id,
            Job.status == "scheduled"
        )
        .update({
            Job.status: "claimed",
            Job.assigned_worker_id: worker_id
        })
    )

    db.session.commit()

    if updated == 0:
        return None

    return job


def execute_job(job):
    print(
        f"Executing job {job.id} "
        f"type={job.job_type} "
        f"payload={job.payload}"
    )

    time.sleep(2)

    print(f"Job {job.id} completed")


def add_log(job, execution, level, message):
    log = JobLog(
        job_id=job.id,
        execution_id=execution.id if execution else None,
        level=level,
        message=message
    )

    db.session.add(log)


def run_worker(worker_id):
    print(f"Worker started: {worker_id}")

    while True:

        job = claim_next_job(worker_id)

        if job is None:
            time.sleep(2)
            continue

        try:
            # Increase attempt count
            job.attempts += 1

            # Create execution record
            execution = JobExecution(
                job_id=job.id,
                worker_id=worker_id,
                attempt=job.attempts,
                status="running",
                started_at=datetime.datetime.utcnow()
            )

            db.session.add(execution)

            # Update job state
            job.status = "running"

            # Add starting log
            add_log(
                job,
                execution,
                "INFO",
                "Job execution started"
            )

            db.session.commit()

            # Execute the actual job
            execute_job(job)

            # Successful execution
            execution.status = "completed"

            execution.finished_at = (
                datetime.datetime.utcnow()
            )

            job.status = "completed"

            add_log(
                job,
                execution,
                "INFO",
                "Job execution completed"
            )

            db.session.commit()

        except Exception as exc:

            print(
                f"Job {job.id} failed: {exc}"
            )

            execution.status = "failed"

            execution.finished_at = (
                datetime.datetime.utcnow()
            )

            execution.error = str(exc)

            job.status = "failed"

            job.last_error = str(exc)

            add_log(
                job,
                execution,
                "ERROR",
                str(exc)
            )

            db.session.commit()


if __name__ == "__main__":

    import argparse

    from . import create_app

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--name",
        required=True
    )

    args = parser.parse_args()

    app = create_app()

    with app.app_context():

        worker = Worker.query.filter_by(
            name=args.name
        ).first()

        if worker is None:

            worker = Worker(
                name=args.name
            )

            db.session.add(worker)

            db.session.commit()

        print(
            f"Worker started: {worker.name}"
        )

        run_worker(worker.id)