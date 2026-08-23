import time

from .extensions import db
from .models import Job
from .models import Job, Worker


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

def run_worker(worker_id):
    print("Worker started")

    while True:
        job = claim_next_job(worker_id)  # Replace with actual worker ID

        if job is None:
            time.sleep(2)
            continue

        job.status = "running"
        db.session.commit()

        try:
            execute_job(job)

            job.status = "completed"
            db.session.commit()

        except Exception as exc:
            job.status = "failed"
            job.last_error = str(exc)
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

        print(f"Worker started: {worker.name}")

        run_worker(worker.id)