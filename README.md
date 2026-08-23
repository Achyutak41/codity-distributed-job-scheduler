# Distributed Job Scheduler

A production-inspired **Distributed Job Scheduler** built with Python,
Flask, SQLAlchemy, SQLite, JWT authentication, and independently
running worker processes.

The system allows authenticated users to create organizations,
projects, queues, and jobs. Independent workers poll the database,
atomically claim eligible jobs, execute them, record execution history,
and retry failed jobs according to configurable retry policies.

The project is designed with a clear separation between the REST API,
database layer, and worker execution layer.

---

## Features

### Authentication

- User registration
- User login
- JWT-based authentication
- Password hashing using Werkzeug
- Protected API endpoints
- Organization-level access control

### Multi-Tenant Organization Structure

```text
User
 |
 v
Organization
 |
 v
Project
 |
 v
Queue
 |
 v
Job
```

Users can work with resources belonging to their authorized
organizations.

### Job Scheduling

- Immediate jobs
- Scheduled jobs using `run_at`
- Job priorities
- Persistent job state
- Job status tracking

### Distributed Workers

- Multiple independent worker processes
- Worker registration
- Worker heartbeats
- Worker status tracking
- Dead worker detection
- Stale job recovery

### Reliability

- Atomic job claiming
- Duplicate claim protection
- Retry support
- Fixed retry policy
- Linear retry policy
- Exponential retry policy
- Configurable maximum attempts
- Dead Letter records
- Durable execution history

### Queue Controls

- Queue pause
- Queue resume
- Concurrency limits
- Per-minute job start limits

### Idempotency

Jobs can be submitted using an `Idempotency-Key`.

Submitting the same job again with the same key returns the existing
logical job instead of creating a duplicate.

### Job Management

- Job listing
- Pagination
- Status filtering
- Priority filtering
- Job type filtering
- Job execution history
- Job logs

### Monitoring

Metrics endpoint providing:

- Total jobs
- Scheduled jobs
- Claimed jobs
- Running jobs
- Completed jobs
- Failed jobs
- Total workers
- Online workers
- Offline workers
- Total queues
- Active queues
- Paused queues

### Testing

Automated tests cover the critical application paths:

- Registration and login
- Job creation
- Idempotent enqueue
- Job pagination
- Metrics
- Queue pause
- Queue resume

---

# Architecture

The system separates the REST API from job execution.

```text
                         Client
                           |
                           v
                  +------------------+
                  |    Flask REST    |
                  |       API        |
                  +--------+---------+
                           |
                           v
                  +------------------+
                  |    SQLAlchemy    |
                  |       ORM        |
                  +--------+---------+
                           |
                           v
                  +------------------+
                  |      SQLite      |
                  |     Database     |
                  +--------+---------+
                           ^
                           |
                     Job polling
                           |
              +------------+------------+
              |                         |
              v                         v
       +-------------+           +-------------+
       |   Worker 1  |           |   Worker 2  |
       +-------------+           +-------------+
              |                         |
              +------------+------------+
                           |
                           v
                    Job Execution
```

The REST API is responsible for accepting and persisting jobs.

Workers are responsible for finding eligible jobs and executing them.

This separation allows multiple workers to operate independently.

---

# Job Lifecycle

A typical job follows this lifecycle:

```text
                 +-----------+
                 | scheduled |
                 +-----+-----+
                       |
                       v
                 +-----------+
                 |  claimed  |
                 +-----+-----+
                       |
                       v
                 +-----------+
                 |  running  |
                 +-----+-----+
                       |
             +---------+---------+
             |                   |
             v                   v
       +-----------+       +-----------+
       | completed |       |  failure  |
       +-----------+       +-----+-----+
                                  |
                                  v
                           Retry Available?
                             /         \
                           yes          no
                           /             \
                          v               v
                    +-----------+   +----------+
                    | scheduled |   |  failed  |
                    +-----------+   +-----+----+
                                          |
                                          v
                                    Dead Letter
```

---

# Technology Stack

## Backend

- Python
- Flask
- Flask-SQLAlchemy
- PyJWT
- Werkzeug

## Database

- SQLite
- SQLAlchemy ORM

## Testing

- pytest

## Runtime

- Python worker processes

---

# Project Structure

```text
Distributed_job_scheduler/
│
├── app/
│   ├── __init__.py
│   ├── auth.py
│   ├── organizations.py
│   ├── projects.py
│   ├── queues.py
│   ├── jobs.py
│   ├── metrics.py
│   ├── worker.py
│   ├── models.py
│   └── extensions.py
│
├── tests/
│   └── test_jobs.py
│
├── docs/
│   ├── API.md
│   ├── ARCHITECTURE.md
│   └── DATABASE.md
│
├── instance/
│   └── scheduler.db
│
├── .env
├── .env.example
├── .gitignore
├── requirements.txt
├── run.py
└── README.md
```

---

# Requirements

Recommended Python version:

```text
Python 3.11+
```

The project can be run inside a Python virtual environment.

---

# Installation

## 1. Clone the repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
```

Enter the project directory:

```bash
cd Distributed_job_scheduler
```

---

## 2. Create a virtual environment

### Windows

```cmd
python -m venv venv
```

Activate it:

```cmd
venv\Scripts\activate
```

You should see:

```text
(venv)
```

in your terminal.

---

## 3. Install dependencies

```cmd
pip install -r requirements.txt
```

---

# Environment Configuration

Create a `.env` file in the project root.

Example:

```env
JWT_SECRET_KEY=replace-with-a-long-random-secret
DATABASE_URL=sqlite:///scheduler.db
```

Use a long, random secret for `JWT_SECRET_KEY`.

Do not commit the real `.env` file to Git.

The repository should contain:

```text
.env.example
```

instead.

Example `.env.example`:

```env
JWT_SECRET_KEY=replace-with-a-long-random-secret
DATABASE_URL=sqlite:///scheduler.db
```

---

# Running the Application

## Start the Flask API

From the project root:

```cmd
python run.py
```

The API will be available at:

```text
http://127.0.0.1:5000
```

---

# Running Workers

The API and workers run separately.

Open another terminal and activate the virtual environment:

```cmd
venv\Scripts\activate
```

Start the first worker:

```cmd
python -m app.worker --name worker-1
```

Example output:

```text
Worker started: worker-1
Worker started: <worker-id>
```

You can start another worker in another terminal:

```cmd
python -m app.worker --name worker-2
```

Multiple workers can operate against the same scheduler database.

---

# Basic API Workflow

The normal workflow is:

```text
Register
   |
   v
Login
   |
   v
Create Organization
   |
   v
Create Project
   |
   v
Create Queue
   |
   v
Create Job
   |
   v
Worker Claims Job
   |
   v
Worker Executes Job
   |
   v
Completed / Retry / Failed
```

---

# Authentication

## Register

Endpoint:

```text
POST /auth/register
```

Request:

```json
{
  "username": "achyuta",
  "password": "hello123"
}
```

Example response:

```json
{
  "message": "User registered successfully",
  "user_id": "..."
}
```

---

# Login

Endpoint:

```text
POST /auth/login
```

Request:

```json
{
  "username": "achyuta",
  "password": "hello123"
}
```

The login response contains a JWT.

Use the returned JWT for protected endpoints:

```text
Authorization: Bearer <JWT_TOKEN>
```

---

# Create Organization

Endpoint:

```text
POST /organizations
```

Headers:

```text
Content-Type: application/json
Authorization: Bearer <JWT_TOKEN>
```

Request:

```json
{
  "name": "Achyuta Tech"
}
```

---

# Create Project

Endpoint:

```text
POST /organizations/{organization_id}/projects
```

Headers:

```text
Content-Type: application/json
Authorization: Bearer <JWT_TOKEN>
```

Request:

```json
{
  "name": "Email Service"
}
```

---

# Create Queue

Endpoint:

```text
POST /projects/{project_id}/queues
```

Headers:

```text
Content-Type: application/json
Authorization: Bearer <JWT_TOKEN>
```

Request:

```json
{
  "name": "email-queue",
  "concurrency_limit": 2,
  "starts_per_minute": 60
}
```

The queue controls how many jobs can execute concurrently and how
many jobs can start within a minute.

---

# Create Job

Endpoint:

```text
POST /queues/{queue_id}/jobs
```

Headers:

```text
Content-Type: application/json
Authorization: Bearer <JWT_TOKEN>
```

Example:

```json
{
  "type": "send_email",
  "payload": {
    "to": "user@example.com",
    "subject": "Hello"
  },
  "priority": 10,
  "max_attempts": 3,
  "retry_policy": "exponential",
  "retry_delay": 2
}
```

The API stores the job and returns its job ID.

The API does not execute the job directly.

The worker is responsible for execution.

---

# Scheduled Jobs

A job can be scheduled using `run_at`.

Example:

```json
{
  "type": "send_email",
  "payload": {
    "to": "user@example.com"
  },
  "run_at": "2026-08-23T21:30:00"
}
```

The worker only considers the job eligible when its scheduled
execution time has been reached.

---

# Job Priority

Jobs can have different priorities.

Example:

```json
{
  "type": "send_email",
  "payload": {},
  "priority": 10
}
```

Higher-priority jobs can be selected before lower-priority jobs
when multiple jobs are eligible.

---

# Idempotent Job Submission

The API supports idempotent job creation using:

```text
Idempotency-Key
```

Example:

```text
Idempotency-Key: payment-001
```

First request:

```text
POST /queues/{queue_id}/jobs
Idempotency-Key: payment-001
```

Result:

```text
201 Created
```

Submitting the same key again:

```text
POST /queues/{queue_id}/jobs
Idempotency-Key: payment-001
```

Result:

```text
200 OK
```

The second request returns the existing logical job instead of
creating another job.

This protects against duplicate submissions caused by retries from
clients.

---

# Retry Policies

The scheduler supports retry policies such as:

```text
fixed
linear
exponential
```

Example:

```json
{
  "type": "send_email",
  "payload": {},
  "max_attempts": 3,
  "retry_policy": "exponential",
  "retry_delay": 2
}
```

An exponential retry can conceptually behave like:

```text
Attempt 1
   |
   | failure
   v
2 seconds
   |
   v
Attempt 2
   |
   | failure
   v
4 seconds
   |
   v
Attempt 3
   |
   | failure
   v
Dead Letter
```

The actual retry state is persisted in the database.

---

# Worker Execution

Workers independently poll for eligible jobs.

A worker:

1. Finds an eligible job.
2. Checks queue state.
3. Checks concurrency limits.
4. Checks start-rate limits.
5. Atomically claims the job.
6. Creates an execution record.
7. Executes the job.
8. Records success or failure.
9. Retries when appropriate.
10. Moves permanently failed jobs to Dead Letter records.

---

# Atomic Job Claiming

Multiple workers may see the same eligible job.

The scheduler prevents duplicate execution using an atomic claim
operation.

Example:

```text
Worker 1                  Worker 2
   |                         |
   |---- claim(job) -------->|
   |                         |
   |      SUCCESS            |
   |                         |
   |                         |---- claim(job)
   |                         |
   |                         |     NO JOB
   |                         |
   v                         v
 owns job                cannot claim
```

Only one worker can successfully claim the job.

---

# Worker Heartbeats

Workers periodically update their heartbeat information.

Conceptually:

```text
Worker
   |
   | heartbeat
   v
Database
```

If a worker stops sending heartbeats:

```text
Worker
   |
   X
heartbeat stops
   |
   v
Worker considered offline
   |
   v
Stale work can be recovered
```

This allows the scheduler to recover jobs from failed workers.

---

# Queue Pause and Resume

## Pause Queue

```text
POST /queues/{queue_id}/pause
```

Example:

```cmd
curl -X POST http://127.0.0.1:5000/queues/YOUR_QUEUE_ID/pause ^
-H "Authorization: Bearer YOUR_JWT_TOKEN"
```

A paused queue prevents workers from claiming new jobs from that
queue.

---

## Resume Queue

```text
POST /queues/{queue_id}/resume
```

Example:

```cmd
curl -X POST http://127.0.0.1:5000/queues/YOUR_QUEUE_ID/resume ^
-H "Authorization: Bearer YOUR_JWT_TOKEN"
```

After resuming, eligible jobs can be claimed again.

---

# List Jobs

Endpoint:

```text
GET /queues/{queue_id}/jobs
```

Example:

```text
GET /queues/{queue_id}/jobs?page=1&per_page=10
```

Response contains:

- jobs
- current page
- page size
- total jobs
- total pages
- next-page information
- previous-page information

---

# Job Filtering

Jobs can be filtered by status.

Example:

```text
GET /queues/{queue_id}/jobs?status=completed
```

Filter by priority:

```text
GET /queues/{queue_id}/jobs?priority=10
```

Filter by type:

```text
GET /queues/{queue_id}/jobs?type=send_email
```

Pagination and filtering can be combined:

```text
GET /queues/{queue_id}/jobs?page=1&per_page=10&status=completed
```

---

# Metrics

Endpoint:

```text
GET /metrics/overview
```

Headers:

```text
Authorization: Bearer <JWT_TOKEN>
```

Example response:

```json
{
  "jobs": {
    "total": 20,
    "scheduled": 3,
    "claimed": 0,
    "running": 2,
    "completed": 14,
    "failed": 1
  },
  "workers": {
    "total": 2,
    "online": 2,
    "offline": 0
  },
  "queues": {
    "total": 3,
    "active": 2,
    "paused": 1
  }
}
```

These metrics can be used by an operations dashboard.

---

# Dead Letter Handling

When a job reaches its maximum number of attempts, it is no longer
retried.

Conceptually:

```text
Job
 |
 v
Attempt 1
 |
 X
 |
 v
Attempt 2
 |
 X
 |
 v
Attempt 3
 |
 X
 |
 v
Dead Letter
```

The Dead Letter record preserves information about the final failure.

---

# Database

The local implementation uses SQLite.

Default database location:

```text
instance/scheduler.db
```

The database contains entities representing:

```text
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
```

For detailed database information, see:

```text
docs/DATABASE.md
```

---

# API Documentation

Complete API information is available in:

```text
docs/API.md
```

The API documentation contains the available routes, request
structures, authentication requirements, and example responses.

---

# Architecture Documentation

Detailed system architecture is available in:

```text
docs/ARCHITECTURE.md
```

---

# Running Automated Tests

Make sure the virtual environment is activated.

Run:

```cmd
python -m pytest -v
```

The current critical-path test suite covers:

```text
test_register_and_login
test_create_job
test_idempotent_enqueue
test_job_pagination
test_metrics
test_queue_pause
test_queue_resume
```

Expected result:

```text
7 passed
```

---

# Example End-to-End Test

A simple end-to-end workflow is:

```text
1. Start Flask API
        |
        v
2. Register user
        |
        v
3. Login
        |
        v
4. Receive JWT
        |
        v
5. Create organization
        |
        v
6. Create project
        |
        v
7. Create queue
        |
        v
8. Start worker
        |
        v
9. Create job
        |
        v
10. Worker claims job
        |
        v
11. Worker executes job
        |
        v
12. Job completed
        |
        v
13. Check metrics
```

---

# Example Worker Test

Open Terminal 1:

```cmd
venv\Scripts\activate
python run.py
```

Open Terminal 2:

```cmd
venv\Scripts\activate
python -m app.worker --name worker-1
```

Create a job from Terminal 3:

```cmd
curl -X POST http://127.0.0.1:5000/queues/YOUR_QUEUE_ID/jobs ^
-H "Content-Type: application/json" ^
-H "Authorization: Bearer YOUR_JWT_TOKEN" ^
-d "{\"type\":\"send_email\",\"payload\":{\"to\":\"user@example.com\"}}"
```

The worker should detect and execute the job.

Example worker output:

```text
Worker started: worker-1

Executing job <job-id>
type=send_email

Job <job-id> completed
```

---

# Production Considerations

The current implementation is designed for a local technical
demonstration and uses SQLite for portability.

A production deployment should consider:

- PostgreSQL or another managed database
- Database migrations
- HTTPS
- Secure secret management
- Structured external logging
- Distributed rate limiting
- Monitoring
- Alerting
- Hosted API
- Hosted frontend
- Process supervision
- Containerization
- Backups
- Database connection pooling

The service boundary and job semantics are designed so that the
database can later be migrated from SQLite to a server database.

For higher-throughput PostgreSQL deployments, row-level locking
strategies such as `SKIP LOCKED` can be considered for worker job
claiming.

---

# Security Considerations

The application uses JWT authentication for protected endpoints.

Passwords are stored using password hashes rather than plaintext
passwords.

The JWT secret must not be hard-coded in source code for production.

Use:

```env
JWT_SECRET_KEY=<strong-random-secret>
```

and keep `.env` outside version control.

Never commit real credentials, API keys, database passwords, or JWT
secrets to Git.

---



# Current Project Status

The core scheduler implementation includes:

- Authentication
- Multi-tenant organizations
- Projects
- Queues
- Jobs
- Workers
- Worker heartbeats
- Atomic job claiming
- Scheduling
- Priority
- Concurrency limits
- Rate limits
- Retries
- Backoff
- Idempotency
- Dead Letter handling
- Job execution history
- Job logs
- Pagination
- Filtering
- Queue pause/resume
- Metrics
- Automated tests
- API documentation
- Architecture documentation
- Database documentation

---

# Repository Documentation

```text
README.md
docs/API.md
docs/ARCHITECTURE.md
docs/DATABASE.md
```

---
