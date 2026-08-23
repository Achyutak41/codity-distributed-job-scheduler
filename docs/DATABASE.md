# Distributed Job Scheduler — Database Design

## 1. Database

Development database:

SQLite

Database file:

instance/scheduler.db

The application uses SQLAlchemy as the ORM.

The current SQLite implementation is intended for local development
and technical-assignment demonstration.

A production deployment should use PostgreSQL or another managed
server database.

---

# 2. Entity Relationship Overview

```text
User
 │
 │
 ▼
Membership
 │
 ▼
Organization
 │
 ▼
Project
 │
 ▼
Queue
 │
 ▼
Job
 │
 ├──────────────► JobExecution
 │                     │
 │                     ▼
 │                  JobLog
 │
 └──────────────► DeadLetter

Worker
 │
 ├──────────────► WorkerHeartbeat
 │
 └──────────────► JobExecution
```

## 3. User

Table:

users

Columns:

| Column | Type | Description |
| :--- | :--- | :--- |
| id | UUID/String | Primary key |
| username | String | Unique username |
| password | String | Password hash |

Relationships:

User → Membership

One user can belong to multiple organizations.

## 4. Organization

Table:

organizations

Columns:

| Column | Type | Description |
| :--- | :--- | :--- |
| id | UUID/String | Primary key |
| name | String | Organization name |

Relationships:

Organization → Membership

Organization → Project

## 5. Membership

Table:

memberships

Columns:

| Column | Type | Description |
| :--- | :--- | :--- |
| id | UUID/String | Primary key |
| user_id | UUID/String | Foreign key to users |
| organization_id | UUID/String | Foreign key to organizations |
| role | String | User role |

Membership provides the relationship between users and organizations.

## 6. Project

Table:

projects

Columns:

| Column | Type | Description |
| :--- | :--- | :--- |
| id | UUID/String | Primary key |
| organization_id | UUID/String | Foreign key |
| name | String | Project name |

Relationships:

Project → Queue

## 7. Queue

Table:

queues

Columns:

| Column | Type | Description |
| :--- | :--- | :--- |
| id | UUID/String | Primary key |
| project_id | UUID/String | Foreign key |
| name | String | Queue name |
| paused | Boolean | Whether queue is paused |
| concurrency_limit | Integer | Maximum simultaneous jobs |
| starts_per_minute | Integer | Maximum starts in rolling minute |

A queue contains jobs waiting to be processed.

## 8. Job

Table:

jobs

Columns:

| Column | Type | Description |
| :--- | :--- | :--- |
| id | UUID/String | Primary key |
| queue_id | UUID/String | Foreign key |
| job_type | String | Job type |
| payload | JSON | Job input |
| priority | Integer | Job priority |
| status | String | Current lifecycle state |
| attempts | Integer | Number of attempts |
| max_attempts | Integer | Maximum attempts |
| retry_policy | String | Retry strategy |
| retry_delay | Integer | Base retry delay |
| next_retry_at | DateTime | Next retry time |
| run_at | DateTime | Scheduled execution time |
| assigned_worker_id | UUID/String | Current worker |
| scheduled_at | DateTime | Scheduling timestamp |
| last_error | Text | Last failure |
| idempotency_key | String | Duplicate submission key |
| created_at | DateTime | Creation time |
| updated_at | DateTime | Last update |

Job lifecycle:

```text
scheduled
    |
    v
claimed
    |
    v
running
    |
    +----------> completed
    |
    +----------> scheduled
                     |
                     | retry
                     v
                  running
                     |
                     v
                   failed
                     |
                     v
                DeadLetter
```

## 9. Worker

Table:

workers

Columns:

| Column | Type | Description |
| :--- | :--- | :--- |
| id | UUID/String | Primary key |
| name | String | Worker name |
| status | String | online/offline |

Workers execute jobs independently from the REST API.

## 10. WorkerHeartbeat

Table:

worker_heartbeats

Columns:

| Column | Type | Description |
| :--- | :--- | :--- |
| id | UUID/String | Primary key |
| worker_id | UUID/String | Worker foreign key |
| last_seen_at | DateTime | Last heartbeat |

The heartbeat allows the scheduler to detect workers that have stopped responding.

## 11. JobExecution

Table:

job_executions

Columns:

| Column | Type | Description |
| :--- | :--- | :--- |
| id | UUID/String | Primary key |
| job_id | UUID/String | Job foreign key |
| worker_id | UUID/String | Worker foreign key |
| attempt | Integer | Attempt number |
| status | String | Execution status |
| started_at | DateTime | Start time |
| finished_at | DateTime | Finish time |
| error | Text | Execution error |

JobExecution provides an audit trail for individual attempts.

## 12. JobLog

Table:

job_logs

Columns:

| Column | Type | Description |
| :--- | :--- | :--- |
| id | UUID/String | Primary key |
| job_id | UUID/String | Job foreign key |
| execution_id | UUID/String | Execution foreign key |
| level | String | Log level |
| message | Text | Log message |
| created_at | DateTime | Creation time |

Logs are retained separately from the Job record.

## 13. DeadLetter

Table:

dead_letters

Columns:

| Column | Type | Description |
| :--- | :--- | :--- |
| id | UUID/String | Primary key |
| job_id | UUID/String | Job foreign key |
| reason | Text | Final failure reason |
| attempts | Integer | Number of attempts |
| created_at | DateTime | Creation time |

A DeadLetter record is created when a job permanently fails.

## 14. Foreign-Key Relationships

```text
users
  │
  └── memberships.user_id

organizations
  │
  ├── memberships.organization_id
  │
  └── projects.organization_id

projects
  │
  └── queues.project_id

queues
  │
  └── jobs.queue_id

workers
  │
  ├── jobs.assigned_worker_id
  ├── worker_heartbeats.worker_id
  └── job_executions.worker_id

jobs
  │
  ├── job_executions.job_id
  ├── job_logs.job_id
  └── dead_letters.job_id

job_executions
  │
  └── job_logs.execution_id
```

## 15. Data Integrity

The database uses:

*   UUID primary keys
*   Foreign keys
*   Unique usernames
*   Unique worker names
*   Cascading ownership relationships
*   Unique worker heartbeat per worker
*   Unique DeadLetter record per job

Idempotent submission uses:

`queue_id` + `idempotency_key`

as the logical identity of a repeated enqueue request.

## 16. Production Database

SQLite is used for local development.

For production:

```text
Application
     |
     v
PostgreSQL
     |
     +---- indexes
     +---- transactions
     +---- row-level locking
```

The worker claim operation should use stronger database locking,
such as PostgreSQL row locking / SKIP LOCKED, when scaling to
multiple workers and higher throughput.

## 17. Database Trade-off

SQLite was selected because it:

*   requires no external database server
*   is easy to run locally
*   is portable
*   is suitable for the technical assignment

A production deployment should use a managed database.
