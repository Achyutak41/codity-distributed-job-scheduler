# Distributed Job Scheduler Architecture

## 1. Overview

The Distributed Job Scheduler is a Flask-based distributed task
execution system.

The system separates:

- REST API
- Database
- Queue management
- Workers
- Job execution
- Monitoring


## 2. High-Level Architecture


                         Client
                           |
                           v
                    +-------------+
                    | Flask REST  |
                    |     API     |
                    +------+------+
                           |
                           v
                    +-------------+
                    | SQLAlchemy  |
                    |    ORM      |
                    +------+------+
                           |
                           v
                    +-------------+
                    |   SQLite    |
                    |  Database   |
                    +-------------+

                           ^
                           |
                    Job polling
                           |
             +-------------+-------------+
             |                           |
             v                           v
       +-----------+               +-----------+
       | Worker 1  |               | Worker 2  |
       +-----------+               +-----------+
             |                           |
             +-------------+-------------+
                           |
                           v
                    Job Execution


## 3. Request Flow

Client sends:

POST /queues/{queue_id}/jobs

The API:

1. Authenticates the user.
2. Validates the request.
3. Checks the queue.
4. Checks idempotency.
5. Creates the job.
6. Returns the job ID.

The API does not execute the job.


## 4. Worker Flow

Workers independently poll the database.

Worker:

1. Finds an eligible job.
2. Checks queue limits.
3. Atomically claims the job.
4. Creates JobExecution.
5. Executes the job.
6. Records success or failure.
7. Retries when necessary.


## 5. Job Lifecycle

scheduled
    |
    v
claimed
    |
    v
running
    |
    +------> completed
    |
    +------> scheduled (retry)
    |
    +------> failed
                    |
                    v
                DeadLetter


## 6. Reliability

The scheduler supports:

- Atomic job claiming
- Worker heartbeats
- Dead worker detection
- Stale job recovery
- Retry policies
- Exponential backoff
- Idempotent enqueue
- Queue pause
- Queue concurrency limits
- Per-minute start limits
- Dead Letter records


## 7. Worker Heartbeats

Workers periodically update:

WorkerHeartbeat.last_seen_at

If the heartbeat becomes stale:

Worker -> offline

Jobs assigned to that worker can be recovered.


## 8. Idempotency

Clients can provide:

Idempotency-Key

The scheduler checks whether the same queue already contains
a job with that key.

If it exists, the existing job is returned.


## 9. Scheduling

Jobs can specify:

run_at

The worker only considers the job eligible when:

current_time >= run_at


## 10. Queue Limits

Queue supports:

concurrency_limit

starts_per_minute

These limits are checked before claiming a job.


## 11. Dead Letter Queue

When a job reaches max_attempts:

Job status -> failed

A DeadLetter record is created containing:

- job ID
- failure reason
- attempt count
- creation timestamp


## 12. Database Entities

User
Organization
Membership
Project
Queue
Job
Worker
WorkerHeartbeat
JobExecution
JobLog
DeadLetter


## 13. Technology Stack

Backend:

Python

Flask

Flask-SQLAlchemy

SQLite

JWT authentication

Workers:

Python processes

Database:

SQLite for local development


## 14. Production Migration

The current implementation uses SQLite for portability.

A production deployment can migrate to PostgreSQL.

The worker/API boundary remains independent of the
underlying database implementation.