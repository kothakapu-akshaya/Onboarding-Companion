"""Tests for the onboarding progress and evidence API endpoints."""

import uuid
from datetime import timedelta
from io import BytesIO
from unittest.mock import Mock, patch

import httpx

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.auth import create_access_token
from app.db.session import get_session
from app.main import app
from app.models.onboarding import OnboardingEvidence, OnboardingProgress

IMAGE_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 128
MAX_EVIDENCE_FILE_SIZE = 5 * 1024 * 1024
MAX_EVIDENCE_PER_TASK = 6
VALID_MIME = "image/png"


def _auth_header(user_id, *, minutes=30):
    token = create_access_token(
        subject=str(user_id), expires_delta=timedelta(minutes=minutes)
    )
    return {"Authorization": f"Bearer {token}"}


def _evidence_rows(engine):
    with Session(engine) as session:
        return session.exec(select(OnboardingEvidence)).all()


def _upload(client, user_id, *, task_key="1", filename="proof.png",
            content_type=VALID_MIME, content=IMAGE_PNG):
    return client.post(
        f"/api/v1/onboarding/tasks/{task_key}/evidence",
        headers=_auth_header(user_id),
        files={"file": (filename, BytesIO(content), content_type)},
    )


@pytest.fixture
def db_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(
        engine,
        tables=[OnboardingProgress.__table__, OnboardingEvidence.__table__],
    )
    yield engine
    engine.dispose()


@pytest.fixture
def api_client(db_engine):
    def override_get_session():
        with Session(db_engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    with patch("app.core.onboarding_deps.httpx.AsyncClient") as mock_client:
        client_instance = mock_client.return_value.__aenter__.return_value

        def corpus_auth(url, *, headers=None, **kwargs):
            headers = headers or {}
            authorization = headers.get("Authorization", "")
            if not authorization.startswith("Bearer "):
                return httpx.Response(
                    401, json={"detail": "Not authenticated"}
                )

            token = authorization.removeprefix("Bearer ")

            if token == "not.a.jwt":
                return httpx.Response(
                    401, json={"detail": "Could not validate credentials"}
                )

            from jose import jwt

            try:
                payload = jwt.get_unverified_claims(token)
                user_id = payload["sub"]
                exp = payload.get("exp")
                if exp is not None:
                    import time

                    if exp <= time.time():
                        return httpx.Response(
                            401, json={"detail": "Could not validate credentials"}
                        )
            except Exception:
                return httpx.Response(
                    401, json={"detail": "Could not validate credentials"}
                )

            return httpx.Response(200, json={"id": user_id})

        client_instance.get.side_effect = corpus_auth

        yield TestClient(app)

    app.dependency_overrides.clear()


@pytest.fixture
def storage(db_engine):
    with patch("app.api.v1.endpoints.onboarding.get_storage_client") as mock_get:
        client = Mock()
        client.upload_file_data.return_value = {"success": True}
        client.get_presigned_url.return_value = "https://presigned.example/read"
        client.delete_object.return_value = True
        mock_get.return_value = client
        yield client


@pytest.fixture
def failing_commit_env(db_engine):
    def _explode_commit():
        raise SQLAlchemyError("simulated database failure")

    def override_get_session():
        session = Session(db_engine)
        session.commit = _explode_commit
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_session] = override_get_session

    with (
        patch("app.api.v1.endpoints.onboarding.get_storage_client") as mock_get,
        patch("app.core.onboarding_deps.httpx.AsyncClient") as mock_client,
    ):
        client = Mock()
        client.upload_file_data.return_value = {"success": True}
        client.delete_object.return_value = True
        mock_get.return_value = client

        client_instance = mock_client.return_value.__aenter__.return_value

        def corpus_auth(url, *, headers=None, **kwargs):
            headers = headers or {}
            authorization = headers.get("Authorization", "")

            if not authorization.startswith("Bearer "):
                return httpx.Response(
                    401, json={"detail": "Not authenticated"}
                )

            token = authorization.removeprefix("Bearer ")

            from jose import jwt
            import time

            try:
                payload = jwt.get_unverified_claims(token)
                user_id = payload["sub"]
                exp = payload.get("exp")

                if exp is not None and exp <= time.time():
                    return httpx.Response(
                        401, json={"detail": "Could not validate credentials"}
                    )
            except Exception:
                return httpx.Response(
                    401, json={"detail": "Could not validate credentials"}
                )

            return httpx.Response(200, json={"id": user_id})

        client_instance.get.side_effect = corpus_auth

        yield TestClient(app), client

    app.dependency_overrides.clear()


# --- Authentication and identity ---


def test_evidence_requires_authentication(api_client):
    response = api_client.get("/api/v1/onboarding/progress")
    assert response.status_code == 401


def test_evidence_rejects_invalid_token(api_client):
    response = api_client.get(
        "/api/v1/onboarding/progress",
        headers={"Authorization": "Bearer not.a.jwt"},
    )
    assert response.status_code == 401


def test_evidence_rejects_expired_token(api_client):
    user_id = uuid.uuid4()
    response = api_client.get(
        "/api/v1/onboarding/progress",
        headers=_auth_header(user_id, minutes=-5),
    )
    assert response.status_code == 401


def test_progress_uses_token_identity(api_client):
    user_id = uuid.uuid4()
    response = api_client.put(
        "/api/v1/onboarding/progress/1",
        headers=_auth_header(user_id),
        json={"status": "in_progress", "notes": "checking"},
    )
    assert response.status_code == 200
    assert response.json()["user_id"] == str(user_id)


# --- Progress persistence ---


def test_progress_create(api_client):
    user_id = uuid.uuid4()
    response = api_client.put(
        "/api/v1/onboarding/progress/4",
        headers=_auth_header(user_id),
        json={"status": "completed", "notes": "finished install"},
    )
    body = response.json()
    assert body["task_key"] == "4"
    assert body["status"] == "completed"
    assert body["notes"] == "finished install"


def test_progress_update_upserts(api_client, db_engine):
    user_id = uuid.uuid4()
    first = api_client.put(
        "/api/v1/onboarding/progress/2",
        headers=_auth_header(user_id),
        json={"status": "in_progress"},
    )
    second = api_client.put(
        "/api/v1/onboarding/progress/2",
        headers=_auth_header(user_id),
        json={"status": "completed", "notes": "done"},
    )
    assert second.json()["id"] == first.json()["id"]
    assert second.json()["status"] == "completed"
    assert second.json()["notes"] == "done"
    with Session(db_engine) as session:
        rows = session.exec(select(OnboardingProgress)).all()
        assert len(rows) == 1


def test_progress_list_returns_saved_progress(api_client):
    user_id = uuid.uuid4()
    headers = _auth_header(user_id)
    api_client.put(
        "/api/v1/onboarding/progress/1", headers=headers,
        json={"status": "completed"},
    )
    api_client.put(
        "/api/v1/onboarding/progress/2", headers=headers,
        json={"status": "in_progress"},
    )
    response = api_client.get("/api/v1/onboarding/progress", headers=headers)
    assert response.status_code == 200
    assert [item["task_key"] for item in response.json()] == ["1", "2"]


def test_progress_isolated_between_users(api_client):
    alice = uuid.uuid4()
    bob = uuid.uuid4()
    api_client.put(
        "/api/v1/onboarding/progress/3",
        headers=_auth_header(alice),
        json={"status": "completed"},
    )
    bob_items = api_client.get(
        "/api/v1/onboarding/progress", headers=_auth_header(bob)
    )
    assert bob_items.status_code == 200
    assert bob_items.json() == []


def test_rejects_unknown_task_key(api_client):
    response = api_client.put(
        "/api/v1/onboarding/progress/99",
        headers=_auth_header(uuid.uuid4()),
        json={"status": "in_progress"},
    )
    assert response.status_code == 400


# --- Evidence lifecycle ---


def test_evidence_upload_creates_metadata(storage, api_client, db_engine):
    user_id = uuid.uuid4()
    content = b"\x89PNG fake bytes" * 8
    response = _upload(api_client, user_id, content=content)
    assert response.status_code == 201
    body = response.json()
    assert body["user_id"] == str(user_id)
    assert body["task_key"] == "1"
    assert body["file_name"] == "proof.png"
    assert body["mime_type"] == VALID_MIME
    assert body["file_size"] == len(content)
    assert body["object_key"].startswith(
        f"onboarding/users/{user_id}/tasks/1/"
    )
    assert body["object_key"].endswith(".png")
    assert len(_evidence_rows(db_engine)) == 1


def test_evidence_metadata_persisted_in_listing(storage, api_client):
    user_id = uuid.uuid4()
    created = _upload(api_client, user_id).json()
    listing = api_client.get(
        "/api/v1/onboarding/tasks/1/evidence",
        headers=_auth_header(user_id),
    )
    assert listing.status_code == 200
    assert listing.json() == [created]


def test_evidence_list_returns_all(storage, api_client):
    user_id = uuid.uuid4()
    _upload(api_client, user_id)
    _upload(api_client, user_id)
    listing = api_client.get(
        "/api/v1/onboarding/tasks/1/evidence",
        headers=_auth_header(user_id),
    )
    assert listing.status_code == 200
    assert len(listing.json()) == 2


def test_evidence_presigned_url_generation(storage, api_client):
    user_id = uuid.uuid4()
    created = _upload(api_client, user_id).json()
    response = api_client.get(
        f"/api/v1/onboarding/tasks/1/evidence/{created['id']}/url",
        headers=_auth_header(user_id),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["evidence_url"] == "https://presigned.example/read"
    assert body["expires_minutes"] == 15
    storage.get_presigned_url.assert_called_once_with(
        created["object_key"], expires=timedelta(minutes=15)
    )


def test_evidence_presigned_url_bounds(storage, api_client):
    user_id = uuid.uuid4()
    created = _upload(api_client, user_id).json()
    for value in (0, 121, 200):
        response = api_client.get(
            f"/api/v1/onboarding/tasks/1/evidence/{created['id']}/url",
            headers=_auth_header(user_id),
            params={"expires_minutes": value},
        )
        assert response.status_code == 422


def test_evidence_delete_removes_object_and_row(storage, api_client, db_engine):
    user_id = uuid.uuid4()
    created = _upload(api_client, user_id).json()
    response = api_client.delete(
        f"/api/v1/onboarding/tasks/1/evidence/{created['id']}",
        headers=_auth_header(user_id),
    )
    assert response.status_code == 204
    storage.delete_object.assert_called_once_with(created["object_key"])
    assert _evidence_rows(db_engine) == []


def test_evidence_cross_user_access_prevented(storage, api_client, db_engine):
    owner = uuid.uuid4()
    intruder = uuid.uuid4()
    created = _upload(api_client, owner).json()

    listing = api_client.get(
        "/api/v1/onboarding/tasks/1/evidence",
        headers=_auth_header(intruder),
    )
    assert listing.json() == []

    url_response = api_client.get(
        f"/api/v1/onboarding/tasks/1/evidence/{created['id']}/url",
        headers=_auth_header(intruder),
    )
    assert url_response.status_code == 404

    delete_response = api_client.delete(
        f"/api/v1/onboarding/tasks/1/evidence/{created['id']}",
        headers=_auth_header(intruder),
    )
    assert delete_response.status_code == 404

    assert len(_evidence_rows(db_engine)) == 1


# --- Validation and failure handling ---


def test_evidence_rejects_unsupported_file(storage, api_client, db_engine):
    user_id = uuid.uuid4()
    bad_extension = _upload(
        api_client, user_id, filename="proof.txt", content_type="text/plain"
    )
    assert bad_extension.status_code == 400
    bad_mime = _upload(
        api_client, user_id, filename="proof.png",
        content_type="image/svg+xml",
    )
    assert bad_mime.status_code == 400
    assert _evidence_rows(db_engine) == []


def test_evidence_rejects_oversized_file(storage, api_client, db_engine):
    user_id = uuid.uuid4()
    oversized = b"\x00" * (MAX_EVIDENCE_FILE_SIZE + 1)
    response = _upload(api_client, user_id, content=oversized)
    assert response.status_code == 413
    assert _evidence_rows(db_engine) == []


def test_evidence_rejects_over_limit(storage, api_client, db_engine):
    user_id = uuid.uuid4()
    for _ in range(MAX_EVIDENCE_PER_TASK):
        assert _upload(api_client, user_id).status_code == 201
    overflow = _upload(api_client, user_id)
    assert overflow.status_code == 400
    assert len(_evidence_rows(db_engine)) == MAX_EVIDENCE_PER_TASK


def test_evidence_storage_failure_is_sanitized(storage, api_client, db_engine):
    user_id = uuid.uuid4()
    storage.upload_file_data.side_effect = Exception(
        "failed to dial storage-secret.example:9000"
    )
    response = _upload(api_client, user_id)
    assert response.status_code == 500
    assert "storage-secret.example" not in response.text
    assert _evidence_rows(db_engine) == []


def test_evidence_upload_rolls_back_on_db_failure(failing_commit_env, db_engine):
    api_client, storage_client = failing_commit_env
    user_id = uuid.uuid4()
    response = _upload(api_client, user_id)
    assert response.status_code == 500
    assert storage_client.delete_object.called
    assert _evidence_rows(db_engine) == []