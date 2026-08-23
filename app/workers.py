import time

from .extensions import db
from .models import Job


def get_next_job():
    return (
        Job.query
        .filter_by(status="scheduled")
        .order_by(
            Job.priority.desc(),
            Job.created_at.asc()
        )
        .first()
    )


def execute_job(job):
    print(
        f"Executing job {job.id} "
        f"type={job.job_type} "
        f"payload={job.payload}"
    )

    time.sleep(2)

    print(f"Job {job.id} completed")

def run_worker():
    print("Worker started")

    while True:
        job = get_next_job()

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
    from . import create_app

    app = create_app()

    with app.app_context():
        run_worker()