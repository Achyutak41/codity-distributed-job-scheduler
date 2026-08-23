import time
import datetime
import argparse
import threading

from sqlalchemy import or_

from .extensions import db

from .models import (
    Job,
    Queue,
    Worker,
    WorkerHeartbeat,
    JobExecution,
    JobLog,
    DeadLetter
)


HEARTBEAT_INTERVAL = 5

DEAD_WORKER_TIMEOUT = 15

# Used by Step 18
DEFAULT_START_WINDOW_SECONDS = 60


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

    changed = False

    for worker in workers:

        heartbeat = worker.heartbeat

        if heartbeat is None:
            continue

        if heartbeat.last_seen_at < cutoff:

            if worker.status != "offline":

                worker.status = "offline"

                changed = True

                print(
                    f"[DEAD WORKER] "
                    f"{worker.name} "
                    f"marked offline"
                )

    if changed:

        db.session.commit()


# =========================================================
# STEP 18
# CONCURRENCY CHECK
# =========================================================

def get_running_count(queue_id):

    return (
        Job.query
        .filter(
            Job.queue_id == queue_id,

            Job.status == "running"
        )
        .count()
    )


def can_start_job(queue):

    # -----------------------------------------------------
    # Queue paused?
    # -----------------------------------------------------

    if queue.paused:

        return False

    # -----------------------------------------------------
    # Concurrency
    # -----------------------------------------------------

    running_count = get_running_count(
        queue.id
    )

    if (
        running_count
        >= queue.concurrency_limit
    ):

        return False

    # -----------------------------------------------------
    # Per-minute start limit
    # -----------------------------------------------------

    window_start = (
        utcnow()
        - datetime.timedelta(
            seconds=DEFAULT_START_WINDOW_SECONDS
        )
    )

    recent_starts = (
        JobExecution.query
        .join(
            Job,
            JobExecution.job_id
            == Job.id
        )
        .filter(
            Job.queue_id == queue.id,

            JobExecution.started_at
            >= window_start
        )
        .count()
    )

    if (
        recent_starts
        >= queue.starts_per_minute
    ):

        return False

    return True


# =========================================================
# STEP 15
# STALE JOB RECOVERY
# =========================================================

def recover_stale_jobs():

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

    recovered = 0

    for job in stale_jobs:

        print(
            f"[STALE JOB] "
            f"{job.id} "
            f"recovered from "
            f"{job.assigned_worker_id}"
        )

        job.status = "scheduled"

        job.assigned_worker_id = None

        job.next_retry_at = utcnow()

        job.last_error = (
            "Recovered because "
            "assigned worker died"
        )

        recovered += 1

    if recovered:

        db.session.commit()

        print(
            f"[RECOVERY] "
            f"{recovered} job(s) recovered"
        )


# =========================================================
# STEP 17
# CLAIM ELIGIBLE JOB
# =========================================================

def claim_next_job(worker_id):

    now = utcnow()

    candidate_jobs = (
        Job.query
        .filter(
            Job.status == "scheduled",

            # ---------------------------------------------
            # Retry delay
            # ---------------------------------------------

            or_(
                Job.next_retry_at.is_(None),

                Job.next_retry_at <= now
            ),

            # ---------------------------------------------
            # STEP 17: schedule
            # ---------------------------------------------

            or_(
                Job.run_at.is_(None),

                Job.run_at <= now
            )
        )
        .order_by(
            # ---------------------------------------------
            # STEP 18: priority
            # ---------------------------------------------

            Job.priority.desc(),

            Job.created_at.asc()
        )
        .all()
    )

    for job in candidate_jobs:

        queue = db.session.get(
            Queue,
            job.queue_id
        )

        if queue is None:

            continue

        # -------------------------------------------------
        # STEP 18
        # Enforce queue limits AT CLAIM TIME
        # -------------------------------------------------

        if not can_start_job(queue):

            continue

        print(
            f"Found eligible job: "
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
                ),

                or_(
                    Job.run_at.is_(None),

                    Job.run_at <= now
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

        if updated == 1:

            print(
                f"[CLAIMED] "
                f"job={job.id} "
                f"worker={worker_id}"
            )

            return db.session.get(
                Job,
                job.id
            )

    return None


# =========================================================
# EXECUTE JOB
# =========================================================

def execute_job(job):

    print(
        f"Executing job {job.id} "
        f"type={job.job_type} "
        f"payload={job.payload}"
    )

    # -----------------------------------------------------
    # Testing: always fail
    # -----------------------------------------------------

    if job.job_type == "fail_test":

        raise Exception(
            "Intentional test failure"
        )

    # -----------------------------------------------------
    # Testing: fail once
    # -----------------------------------------------------

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

    db.session.add(
        log
    )


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
# STEP 19
# DEAD LETTER
# =========================================================

def move_to_dead_letter(
    job,
    reason
):

    existing = (
        DeadLetter.query
        .filter_by(
            job_id=job.id
        )
        .first()
    )

    if existing:

        return

    dead_letter = DeadLetter(

        job_id=job.id,

        reason=reason,

        attempts=job.attempts,

        created_at=utcnow()
    )

    db.session.add(
        dead_letter
    )

    print(
        f"[DEAD LETTER] "
        f"Job {job.id} "
        f"moved to dead-letter queue"
    )


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
        # Health checks
        # -------------------------------------------------

        if loop_counter % 3 == 0:

            detect_dead_workers()

            recover_stale_jobs()

        # -------------------------------------------------
        # Find job
        # -------------------------------------------------

        job = claim_next_job(
            worker_id
        )

        if job is None:

            time.sleep(2)

            continue

        execution = None

        try:

            # ---------------------------------------------
            # Increment attempt
            # ---------------------------------------------

            job.attempts += 1

            # ---------------------------------------------
            # Execution record
            # ---------------------------------------------

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

            # ---------------------------------------------
            # Execute
            # ---------------------------------------------

            execute_job(job)

            # ---------------------------------------------
            # Success
            # ---------------------------------------------

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
                f"[SUCCESS] "
                f"Job {job.id} completed"
            )

        except Exception as exc:

            print(
                f"[FAILURE] "
                f"Job {job.id}: "
                f"{exc}"
            )

            if execution:

                execution.status = "failed"

                execution.finished_at = utcnow()

                execution.error = str(exc)

            job.last_error = str(exc)

            # -------------------------------------------------
            # RETRY
            # -------------------------------------------------

            if (
                job.attempts
                < job.max_attempts
            ):

                delay = (
                    calculate_retry_delay(
                        job
                    )
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
                        "Retry scheduled "
                        f"after {delay} seconds"
                    )
                )

                db.session.commit()

                print(
                    f"[RETRY] "
                    f"Job {job.id} "
                    f"in {delay}s"
                )

            # -------------------------------------------------
            # STEP 19
            # PERMANENT FAILURE
            # -------------------------------------------------

            else:

                job.status = "failed"

                job.next_retry_at = None

                add_log(
                    job,
                    execution,
                    "ERROR",
                    "Maximum attempts reached"
                )

                move_to_dead_letter(
                    job,
                    (
                        "Maximum retry attempts "
                        "reached: "
                        f"{job.last_error}"
                    )
                )

                db.session.commit()

                print(
                    f"[FAILED] "
                    f"Job {job.id} "
                    f"permanently failed"
                )


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