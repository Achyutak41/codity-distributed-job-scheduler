import pytest

from app import create_app
from app.extensions import db

from app.models import (
    User,
    Organization,
    Membership,
    Project,
    Queue,
    Job
)


@pytest.fixture
def app():

    app = create_app()

    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        JWT_SECRET_KEY="test-secret"
    )

    with app.app_context():

        db.drop_all()

        db.create_all()

        yield app

        db.session.remove()

        db.drop_all()


@pytest.fixture
def client(app):

    return app.test_client()


# =========================================================
# HELPER
# =========================================================

def create_user_and_login(client):

    response = client.post(
        "/auth/register",
        json={
            "username": "testuser",
            "password": "test123"
        }
    )

    assert response.status_code == 201

    response = client.post(
        "/auth/login",
        json={
            "username": "testuser",
            "password": "test123"
        }
    )

    assert response.status_code == 200

    data = response.get_json()

    token = (
        data.get("token")
        or data.get("access_token")
    )

    assert token is not None, (
        f"Login response does not contain "
        f"a token: {data}"
    )

    return token


def create_queue(app):

    with app.app_context():

        user = User.query.filter_by(
            username="testuser"
        ).first()

        organization = Organization(
            name="Test Organization"
        )

        db.session.add(
            organization
        )

        db.session.flush()

        membership = Membership(
            user_id=user.id,
            organization_id=organization.id,
            role="owner"
        )

        db.session.add(
            membership
        )

        project = Project(
            organization_id=organization.id,
            name="Test Project"
        )

        db.session.add(
            project
        )

        db.session.flush()

        queue = Queue(
            project_id=project.id,
            name="Test Queue",
            concurrency_limit=2,
            starts_per_minute=60
        )

        db.session.add(
            queue
        )

        db.session.commit()

        return queue.id


# =========================================================
# TEST 1
# AUTHENTICATION
# =========================================================

def test_register_and_login(client):

    token = create_user_and_login(
        client
    )

    assert token is not None

    assert len(token) > 10


# =========================================================
# TEST 2
# CREATE JOB
# =========================================================

def test_create_job(
    app,
    client
):

    token = create_user_and_login(
        client
    )

    queue_id = create_queue(
        app
    )

    response = client.post(

        f"/queues/{queue_id}/jobs",

        headers={
            "Authorization":
                f"Bearer {token}"
        },

        json={
            "type":
                "send_email",

            "payload": {
                "to":
                    "test@example.com"
            }
        }
    )

    assert response.status_code == 201

    data = response.get_json()

    assert data["job_id"] is not None

    assert data["status"] == "scheduled"


# =========================================================
# TEST 3
# IDEMPOTENCY
# =========================================================

def test_idempotent_enqueue(
    app,
    client
):

    token = create_user_and_login(
        client
    )

    queue_id = create_queue(
        app
    )

    headers = {

        "Authorization":
            f"Bearer {token}",

        "Idempotency-Key":
            "idem-test-001"
    }

    payload = {

        "type":
            "send_email",

        "payload": {
            "to":
                "test@example.com"
        }
    }

    first = client.post(

        f"/queues/{queue_id}/jobs",

        headers=headers,

        json=payload
    )

    assert first.status_code == 201

    first_data = first.get_json()

    second = client.post(

        f"/queues/{queue_id}/jobs",

        headers=headers,

        json=payload
    )

    assert second.status_code == 200

    second_data = second.get_json()

    assert (
        first_data["job_id"]
        ==
        second_data["job_id"]
    )


# =========================================================
# TEST 4
# PAGINATION
# =========================================================

def test_job_pagination(
    app,
    client
):

    token = create_user_and_login(
        client
    )

    queue_id = create_queue(
        app
    )

    headers = {
        "Authorization":
            f"Bearer {token}"
    }

    for i in range(5):

        response = client.post(

            f"/queues/{queue_id}/jobs",

            headers=headers,

            json={
                "type":
                    "test_job",

                "payload": {
                    "number": i
                }
            }
        )

        assert response.status_code == 201

    response = client.get(

        f"/queues/{queue_id}/jobs"
        "?page=1&per_page=2",

        headers=headers
    )

    assert response.status_code == 200

    data = response.get_json()

    assert len(
        data["jobs"]
    ) == 2

    assert (
        data["pagination"]["total"]
        == 5
    )


# =========================================================
# TEST 5
# METRICS
# =========================================================

def test_metrics(
    app,
    client
):

    token = create_user_and_login(
        client
    )

    headers = {
        "Authorization":
            f"Bearer {token}"
    }

    response = client.get(

        "/metrics/overview",

        headers=headers
    )

    assert response.status_code == 200

    data = response.get_json()

    assert "jobs" in data

    assert "workers" in data

    assert "queues" in data


# =========================================================
# TEST 6
# QUEUE PAUSE
# =========================================================

def test_queue_pause(
    app,
    client
):

    token = create_user_and_login(
        client
    )

    queue_id = create_queue(
        app
    )

    headers = {
        "Authorization":
            f"Bearer {token}"
    }

    response = client.post(

        f"/queues/{queue_id}/pause",

        headers=headers
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["paused"] is True

    # Job creation should now fail

    response = client.post(

        f"/queues/{queue_id}/jobs",

        headers=headers,

        json={
            "type":
                "send_email",

            "payload": {}
        }
    )

    assert response.status_code == 409


# =========================================================
# TEST 7
# QUEUE RESUME
# =========================================================

def test_queue_resume(
    app,
    client
):

    token = create_user_and_login(
        client
    )

    queue_id = create_queue(
        app
    )

    headers = {
        "Authorization":
            f"Bearer {token}"
    }

    client.post(

        f"/queues/{queue_id}/pause",

        headers=headers
    )

    response = client.post(

        f"/queues/{queue_id}/resume",

        headers=headers
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["paused"] is False