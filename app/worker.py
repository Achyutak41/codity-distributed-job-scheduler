import time
import datetime
import argparse
import threading

from sqlalchemy import or_

from .extensions import db

from .models import (
    Job,
    Worker,
    WorkerHeartbeat,
    JobExecution,
    JobLog
)


HEARTBEAT_INTERVAL = 5

DEAD_WORKER_TIMEOUT = 15

STALE_JOB_TIMEOUT = 20


def utcnow():
    return datetime.datetime.now(
        datetime.timezone.utc
    ).replace(tzinfo=None)


# =========================================================
# HEARTBEAT
# =========================================================

def send_heartbeat(worker_id):

    heartbeat = (
        WorkerHeartbeat.query
        .filter_by(
            worker_id=worker_id
        )
        .first()
    )

    if heartbeat is None:

        heartbeat = WorkerHeartbeat(
            worker_id=worker_id,
            last_seen_at=utcnow()
        )

        db.session.add(
            heartbeat
        )

    else:

        heartbeat.last_seen_at = utcnow()

    worker = db.session.get(
        Worker,
        worker_id
    )

    if worker:

        worker.status = "online"

    db.session.commit()


def heartbeat_loop(
    app,
    worker_id,
    stop_event
):

    while not stop_event.is_set():

        try:

            with app.app_context():

                send_heartbeat(
                    worker_id
                )

                print(
                    f"[HEARTBEAT] "
                    f"worker={worker_id} "
                    f"alive"
                )

        except Exception as exc:

            print(
                f"[HEARTBEAT ERROR] "
                f"{exc}"
            )

        stop_event.wait(
            HEARTBEAT_INTERVAL
        )


# =========================================================
# DEAD WORKER DETECTION
# =========================================================

def detect_dead_workers():

    cutoff = (
        utcnow()
        - datetime.timedelta(
            seconds=DEAD_WORKER_TIMEOUT
        )
    )

    workers = Worker.query.all()

    dead_workers = []

    for worker in workers:

        heartbeat = worker.heartbeat

        if heartbeat is None:
            continue

        if heartbeat.last_seen_at < cutoff:

            if worker.status != "offline":

                worker.status = "offline"

                dead_workers.append(
                    worker
                )

                print(
                    f"[DEAD WORKER] "
                    f"{worker.name} "
                    f"marked offline"
                )

    if dead_workers:

        db.session.commit()

    return dead_workers


# =========================================================
# STALE JOB RECOVERY
# =========================================================

def recover_stale_jobs():

    """
    Find jobs that are still marked as running
    or claimed by workers whose heartbeat is dead.

    Those jobs become eligible for another worker.
    """

    cutoff = (
        utcnow()
        - datetime.timedelta(
            seconds=DEAD_WORKER_TIMEOUT
        )
    )

    stale_jobs = (
        Job.query
        .join(
            Worker,
            Job.assigned_worker_id
            == Worker.id
        )
        .join(
            WorkerHeartbeat,
            WorkerHeartbeat.worker_id
            == Worker.id
        )
        .filter(
            Job.status.in_(
                ["claimed", "running"]
            ),

            WorkerHeartbeat.last_seen_at
            < cutoff
        )
        .all()
    )

    recovered_count = 0

    for job in stale_jobs:

        old_worker = job.assigned_worker_id

        print(
            f"[STALE JOB] "
            f"Job {job.id} "
            f"was owned by dead worker "
            f"{old_worker}"
        )

        job.status = "scheduled"

        job.assigned_worker_id = None

        job.next_retry_at = utcnow()

        job.last_error = (
            "Worker became unavailable "
            "during execution"
        )

        recovered_count += 1

    if recovered_count:

        db.session.commit()

        print(
            f"[RECOVERY] "
            f"Recovered {recovered_count} "
            f"stale job(s)"
        )

    return recovered_count


# =========================================================
# JOB CLAIMING
# =========================================================

def claim_next_job(worker_id):

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
        f"Found scheduled job: "
        f"{job.id}"
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
                Job.status:
                    "claimed",

                Job.assigned_worker_id:
                    worker_id
            },

            synchronize_session=False
        )
    )

    db.session.commit()

    print(
        f"Claim update result: "
        f"{updated}"
    )

    if updated == 0:

        return None

    return db.session.get(
        Job,
        job.id
    )


# =========================================================
# JOB EXECUTION
# =========================================================

def execute_job(job):

    print(
        f"Executing job {job.id} "
        f"type={job.job_type} "
        f"payload={job.payload}"
    )

    if job.job_type == "fail_test":

        raise Exception(
            "Intentional test failure"
        )

    if job.job_type == "fail_once":

        previous_attempts = (
            JobExecution.query
            .filter(
                JobExecution.job_id
                == job.id
            )
            .count()
        )

        if previous_attempts == 1:

            raise Exception(
                "Intentional first-attempt failure"
            )

    time.sleep(2)

    print(
        f"Job {job.id} completed"
    )


# =========================================================
# LOGGING
# =========================================================

def add_log(
    job,
    execution,
    level,
    message
):

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


# =========================================================
# RETRY BACKOFF
# =========================================================

def calculate_retry_delay(job):

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
            * (
                2
                ** (job.attempts - 1)
            )
        )

    return job.retry_delay


# =========================================================
# WORKER LOOP
# =========================================================

def run_worker(
    worker_id,
    worker_name
):

    print(
        f"Worker started: "
        f"{worker_name} "
        f"({worker_id})"
    )

    loop_counter = 0

    while True:

        loop_counter += 1

        # -------------------------------------------------
        # Every few cycles check dead workers
        # -------------------------------------------------

        if loop_counter % 3 == 0:

            detect_dead_workers()

            recover_stale_jobs()

        # -------------------------------------------------
        # Claim job
        # -------------------------------------------------

        job = claim_next_job(
            worker_id
        )

        if job is None:

            time.sleep(2)

            continue

        execution = None

        try:

            job.attempts += 1

            execution = JobExecution(
                job_id=job.id,

                worker_id=worker_id,

                attempt=job.attempts,

                status="running",

                started_at=utcnow()
            )

            db.session.add(
                execution
            )

            job.status = "running"

            add_log(
                job,
                execution,
                "INFO",
                "Job execution started"
            )

            db.session.commit()

            execute_job(job)

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
                f"Job {job.id} "
                f"failed: {exc}"
            )

            if execution is not None:

                execution.status = "failed"

                execution.finished_at = utcnow()

                execution.error = str(exc)

            job.last_error = str(exc)

            if (
                job.attempts
                < job.max_attempts
            ):

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
                    f"Retrying job "
                    f"{job.id} "
                    f"in {delay} seconds"
                )

            else:

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
                    f"permanently failed"
                )

            db.session.commit()


# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description=
        "Distributed Job Scheduler Worker"
    )

    parser.add_argument(
        "--name",
        required=True,
        help="Worker name"
    )

    args = parser.parse_args()

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

            db.session.add(
                worker
            )

            db.session.commit()

        else:

            worker.status = "online"

            db.session.commit()

        stop_event = threading.Event()

        heartbeat_thread = threading.Thread(
            target=heartbeat_loop,
            args=(
                app,
                worker.id,
                stop_event
            ),
            daemon=True
        )

        heartbeat_thread.start()

        try:

            run_worker(
                worker.id,
                worker.name
            )

        except KeyboardInterrupt:

            print(
                "\nStopping worker..."
            )

            stop_event.set()

            worker.status = "offline"

            db.session.commit()

            print(
                "Worker stopped."
            )