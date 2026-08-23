import uuid

from .extensions import db


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