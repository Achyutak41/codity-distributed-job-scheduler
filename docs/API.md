# Distributed Job Scheduler API

Base URL:

http://127.0.0.1:5000

Authentication:

JWT Bearer Token

Example:

Authorization: Bearer <JWT_TOKEN>


# Authentication

## Register

POST /auth/register

Request:

{
  "username": "achyuta",
  "password": "hello123"
}

Response:

201

{
  "message": "User registered successfully",
  "user_id": "..."
}


## Login

POST /auth/login

Request:

{
  "username": "achyuta",
  "password": "hello123"
}

Response:

200

{
  "token": "..."
}


# Organizations

## Create Organization

POST /organizations

Headers:

Authorization: Bearer <JWT_TOKEN>

Request:

{
  "name": "Achyuta Tech"
}


# Projects

## Create Project

POST /organizations/{organization_id}/projects

Headers:

Authorization: Bearer <JWT_TOKEN>

Request:

{
  "name": "Email Service"
}


# Queues

## Create Queue

POST /projects/{project_id}/queues

Headers:

Authorization: Bearer <JWT_TOKEN>

Request:

{
  "name": "email-queue",
  "concurrency_limit": 2,
  "starts_per_minute": 60
}


## Pause Queue

POST /queues/{queue_id}/pause

Headers:

Authorization: Bearer <JWT_TOKEN>


## Resume Queue

POST /queues/{queue_id}/resume

Headers:

Authorization: Bearer <JWT_TOKEN>


# Jobs

## Create Job

POST /queues/{queue_id}/jobs

Headers:

Authorization: Bearer <JWT_TOKEN>

Optional:

Idempotency-Key: payment-001

Request:

{
  "type": "send_email",
  "payload": {
    "to": "user@example.com"
  },
  "priority": 10,
  "max_attempts": 3,
  "retry_policy": "exponential",
  "retry_delay": 2,
  "run_at": "2026-08-23T21:30:00"
}


## List Jobs

GET /queues/{queue_id}/jobs

Query parameters:

page

per_page

status

priority

type


Example:

GET /queues/{queue_id}/jobs?page=1&per_page=10&status=completed


# Metrics

## Overview

GET /metrics/overview

Headers:

Authorization: Bearer <JWT_TOKEN>

Response:

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