import uuid
import datetime

from .extensions import db


def utcnow():
    """
    Return current UTC time as a naive datetime.

    SQLite is currently using naive DateTime columns in this project.
    """
    return datetime.datetime.now(datetime.timezone.utc).replace(
        tzinfo=None
    )


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(
        db.String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    username = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )

    password = db.Column(
        db.String(255),
        nullable=False
    )

    memberships = db.relationship(
        "Membership",
        back_populates="user",
        cascade="all, delete-orphan"
    )


class Organization(db.Model):
    __tablename__ = "organizations"

    id = db.Column(
        db.String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    name = db.Column(
        db.String(150),
        unique=True,
        nullable=False
    )

    memberships = db.relationship(
        "Membership",
        back_populates="organization",
        cascade="all, delete-orphan"
    )

    projects = db.relationship(
        "Project",
        back_populates="organization",
        cascade="all, delete-orphan"
    )


class Membership(db.Model):
    __tablename__ = "memberships"

    id = db.Column(
        db.String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    user_id = db.Column(
        db.String(36),
        db.ForeignKey("users.id"),
        nullable=False
    )

    organization_id = db.Column(
        db.String(36),
        db.ForeignKey("organizations.id"),
        nullable=False
    )

    role = db.Column(
        db.String(50),
        nullable=False,
        default="member"
    )

    user = db.relationship(
        "User",
        back_populates="memberships"
    )

    organization = db.relationship(
        "Organization",
        back_populates="memberships"
    )


class Project(db.Model):
    __tablename__ = "projects"

    id = db.Column(
        db.String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    organization_id = db.Column(
        db.String(36),
        db.ForeignKey("organizations.id"),
        nullable=False
    )

    name = db.Column(
        db.String(150),
        nullable=False
    )

    organization = db.relationship(
        "Organization",
        back_populates="projects"
    )

    queues = db.relationship(
        "Queue",
        back_populates="project",
        cascade="all, delete-orphan"
    )


class Queue(db.Model):
    __tablename__ = "queues"

    id = db.Column(
        db.String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    project_id = db.Column(
        db.String(36),
        db.ForeignKey("projects.id"),
        nullable=False
    )

    name = db.Column(
        db.String(150),
        nullable=False
    )

    paused = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    project = db.relationship(
        "Project",
        back_populates="queues"
    )

    jobs = db.relationship(
        "Job",
        back_populates="queue",
        cascade="all, delete-orphan"
    )


class Job(db.Model):
    __tablename__ = "jobs"

    id = db.Column(
        db.String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    queue_id = db.Column(
        db.String(36),
        db.ForeignKey("queues.id"),
        nullable=False
    )

    job_type = db.Column(
        db.String(100),
        nullable=False
    )

    payload = db.Column(
        db.JSON,
        nullable=False
    )

    priority = db.Column(
        db.Integer,
        default=0,
        nullable=False
    )

    status = db.Column(
        db.String(30),
        default="scheduled",
        nullable=False
    )

    attempts = db.Column(
        db.Integer,
        default=0,
        nullable=False
    )

    max_attempts = db.Column(
        db.Integer,
        default=3,
        nullable=False
    )

    retry_policy = db.Column(
        db.String(30),
        default="exponential",
        nullable=False
    )

    retry_delay = db.Column(
        db.Integer,
        default=2,
        nullable=False
    )

    next_retry_at = db.Column(
        db.DateTime,
        nullable=True
    )

    assigned_worker_id = db.Column(
        db.String(36),
        db.ForeignKey("workers.id"),
        nullable=True
    )

    scheduled_at = db.Column(
        db.DateTime,
        nullable=True
    )

    last_error = db.Column(
        db.Text,
        nullable=True
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=utcnow
    )

    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=utcnow,
        onupdate=utcnow
    )

    queue = db.relationship(
        "Queue",
        back_populates="jobs"
    )

    assigned_worker = db.relationship(
        "Worker",
        back_populates="jobs"
    )

    executions = db.relationship(
        "JobExecution",
        back_populates="job",
        cascade="all, delete-orphan"
    )

    logs = db.relationship(
        "JobLog",
        back_populates="job",
        cascade="all, delete-orphan"
    )


class Worker(db.Model):
    __tablename__ = "workers"

    id = db.Column(
        db.String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    name = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )

    status = db.Column(
        db.String(30),
        default="online",
        nullable=False
    )

    jobs = db.relationship(
        "Job",
        back_populates="assigned_worker"
    )

    executions = db.relationship(
        "JobExecution",
        back_populates="worker",
        cascade="all, delete-orphan"
    )


class JobExecution(db.Model):
    __tablename__ = "job_executions"

    id = db.Column(
        db.String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    job_id = db.Column(
        db.String(36),
        db.ForeignKey("jobs.id"),
        nullable=False
    )

    worker_id = db.Column(
        db.String(36),
        db.ForeignKey("workers.id"),
        nullable=False
    )

    attempt = db.Column(
        db.Integer,
        nullable=False
    )

    status = db.Column(
        db.String(30),
        nullable=False
    )

    started_at = db.Column(
        db.DateTime,
        nullable=False,
        default=utcnow
    )

    finished_at = db.Column(
        db.DateTime,
        nullable=True
    )

    error = db.Column(
        db.Text,
        nullable=True
    )

    job = db.relationship(
        "Job",
        back_populates="executions"
    )

    worker = db.relationship(
        "Worker",
        back_populates="executions"
    )

    logs = db.relationship(
        "JobLog",
        back_populates="execution",
        cascade="all, delete-orphan"
    )


class JobLog(db.Model):
    __tablename__ = "job_logs"

    id = db.Column(
        db.String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    job_id = db.Column(
        db.String(36),
        db.ForeignKey("jobs.id"),
        nullable=False
    )

    execution_id = db.Column(
        db.String(36),
        db.ForeignKey("job_executions.id"),
        nullable=True
    )

    level = db.Column(
        db.String(20),
        nullable=False,
        default="INFO"
    )

    message = db.Column(
        db.Text,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=utcnow
    )

    job = db.relationship(
        "Job",
        back_populates="logs"
    )

    execution = db.relationship(
        "JobExecution",
        back_populates="logs"
    )