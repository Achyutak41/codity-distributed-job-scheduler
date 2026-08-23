import time
import datetime
import argparse

from sqlalchemy import or_

from .extensions import db

from .models import (
    Job,
    Worker,
    JobExecution,
    JobLog
)


def utcnow():
    """
    Return current UTC time as a naive datetime.

    Our SQLite DateTime columns currently use naive values.
    """
    return datetime.datetime.now(
        datetime.timezone.utc
    ).replace(tzinfo=None)


# ---------------------------------------------------------
# Job Claiming
# ---------------------------------------------------------

def claim_next_job(worker_id):
    """
    Find one eligible scheduled job and atomically claim it.

    Only one worker should successfully change the job
    from scheduled -> claimed.
    """

    now = utcnow()

    job = (
        Job.query
        .filter(
            Job.status == "scheduled",
            or_(
                Job.next_retry_at.is_(None),
                Job.next_retry_at <= now
            )
        )
        .order_by(
            Job.priority.desc(),
            Job.created_at.asc()
        )
        .first()
    )

    if job is None:
        return None

    print(
        f"Found scheduled job: {job.id}"
    )

    updated = (
        db.session.query(Job)
        .filter(
            Job.id == job.id,
            Job.status == "scheduled",
            or_(
                Job.next_retry_at.is_(None),
                Job.next_retry_at <= now
            )
        )
        .update(
            {
                Job.status: "claimed",
                Job.assigned_worker_id: worker_id
            },
            synchronize_session=False
        )
    )

    db.session.commit()

    print(
        f"Claim update result: {updated}"
    )

    if updated == 0:
        return None

    return Job.query.get(job.id)


# ---------------------------------------------------------
# Job Execution
# ---------------------------------------------------------

def execute_job(job):
    """
    Simulate execution of a job.

    fail_test:
        Always fails.

    fail_once:
        Fails on the first attempt and succeeds afterward.

    Any other job type:
        Succeeds normally.
    """

    print(
        f"Executing job {job.id} "
        f"type={job.job_type} "
        f"payload={job.payload}"
    )

    # ---------------------------------------------
    # Testing: always fail
    # ---------------------------------------------

    if job.job_type == "fail_test":
        raise Exception(
            "Intentional test failure"
        )

    # ---------------------------------------------
    # Testing: fail once
    # ---------------------------------------------

    if job.job_type == "fail_once":

        # Store the number of executions using
        # the database execution history.
        previous_attempts = (
            JobExecution.query
            .filter(
                JobExecution.job_id == job.id
            )
            .count()
        )

        if previous_attempts == 1:
            raise Exception(
                "Intentional first-attempt failure"
            )

    # ---------------------------------------------
    # Normal job simulation
    # ---------------------------------------------

    time.sleep(2)

    print(
        f"Job {job.id} completed"
    )


# ---------------------------------------------------------
# Job Logging
# ---------------------------------------------------------

def add_log(
    job,
    execution,
    level,
    message
):
    """
    Create a JobLog record.
    """

    log = JobLog(
        job_id=job.id,
        execution_id=(
            execution.id
            if execution
            else None
        ),
        level=level,
        message=message
    )

    db.session.add(log)


# ---------------------------------------------------------
# Retry Backoff
# ---------------------------------------------------------

def calculate_retry_delay(job):
    """
    Calculate the delay before the next retry.

    fixed:
        delay = retry_delay

    linear:
        delay = retry_delay * attempts

    exponential:
        delay = retry_delay * 2^(attempts - 1)
    """

    if job.retry_policy == "fixed":
        return job.retry_delay

    if job.retry_policy == "linear":
        return (
            job.retry_delay
            * job.attempts
        )

    if job.retry_policy == "exponential":
        return (
            job.retry_delay
            * (2 ** (job.attempts - 1))
        )

    # Safety fallback
    return job.retry_delay


# ---------------------------------------------------------
# Worker Loop
# ---------------------------------------------------------

def run_worker(worker_id, worker_name):
    """
    Continuously poll for scheduled jobs.
    """

    print(
        f"Worker started: "
        f"{worker_name} ({worker_id})"
    )

    while True:

        job = claim_next_job(
            worker_id
        )

        # No available job
        if job is None:

            time.sleep(2)

            continue

        execution = None

        try:

            # -----------------------------------------
            # Increment attempt
            # -----------------------------------------

            job.attempts += 1

            # -----------------------------------------
            # Create execution history
            # -----------------------------------------

            execution = JobExecution(
                job_id=job.id,
                worker_id=worker_id,
                attempt=job.attempts,
                status="running",
                started_at=utcnow()
            )

            db.session.add(execution)

            # -----------------------------------------
            # Update Job
            # -----------------------------------------

            job.status = "running"

            # -----------------------------------------
            # Log start
            # -----------------------------------------

            add_log(
                job,
                execution,
                "INFO",
                "Job execution started"
            )

            db.session.commit()

            # -----------------------------------------
            # Execute
            # -----------------------------------------

            execute_job(job)

            # -----------------------------------------
            # Successful execution
            # -----------------------------------------

            execution.status = "completed"

            execution.finished_at = utcnow()

            job.status = "completed"

            job.next_retry_at = None

            add_log(
                job,
                execution,
                "INFO",
                "Job execution completed"
            )

            db.session.commit()

            print(
                f"Job {job.id} "
                f"completed successfully"
            )

        except Exception as exc:

            print(
                f"Job {job.id} failed: {exc}"
            )

            # -----------------------------------------
            # Record failed execution
            # -----------------------------------------

            if execution is not None:

                execution.status = "failed"

                execution.finished_at = utcnow()

                execution.error = str(exc)

            # -----------------------------------------
            # Save latest error
            # -----------------------------------------

            job.last_error = str(exc)

            # -----------------------------------------
            # Determine whether retry is possible
            # -----------------------------------------

            if job.attempts < job.max_attempts:

                delay = calculate_retry_delay(
                    job
                )

                job.next_retry_at = (
                    utcnow()
                    + datetime.timedelta(
                        seconds=delay
                    )
                )

                job.status = "scheduled"

                add_log(
                    job,
                    execution,
                    "ERROR",
                    (
                        "Job failed. "
                        f"Retrying in {delay} seconds."
                    )
                )

                print(
                    f"Retrying job {job.id} "
                    f"in {delay} seconds "
                    f"(attempt "
                    f"{job.attempts + 1}"
                    f"/{job.max_attempts})"
                )

            else:

                # -------------------------------------
                # Retry limit reached
                # -------------------------------------

                job.status = "failed"

                job.next_retry_at = None

                add_log(
                    job,
                    execution,
                    "ERROR",
                    "Maximum retry attempts reached"
                )

                print(
                    f"Job {job.id} "
                    f"permanently failed after "
                    f"{job.attempts} attempts"
                )

            db.session.commit()


# ---------------------------------------------------------
# Worker Entry Point
# ---------------------------------------------------------

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Distributed Job Scheduler Worker"
    )

    parser.add_argument(
        "--name",
        required=True,
        help="Worker name"
    )

    args = parser.parse_args()

    # Import here to avoid circular imports
    from . import create_app

    app = create_app()

    with app.app_context():

        worker = (
            Worker.query
            .filter_by(
                name=args.name
            )
            .first()
        )

        if worker is None:

            worker = Worker(
                name=args.name,
                status="online"
            )

            db.session.add(worker)

            db.session.commit()

        else:

            worker.status = "online"

            db.session.commit()

        run_worker(
            worker.id,
            worker.name
        )