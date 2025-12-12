"""TDD tests for API endpoints.

Tests the FastAPI REST API with async job queue pattern.
POST /api/segment returns 202 Accepted with job ID.
GET /api/jobs/{id} returns job status/progress/results.
"""

from collections.abc import Generator
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from stroke_deepisles_demo.api import app
from stroke_deepisles_demo.api.job_store import init_job_store


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Create test client for FastAPI app with fresh job store."""
    with TemporaryDirectory() as tmpdir:
        # Initialize a fresh job store for each test
        store = init_job_store(results_dir=Path(tmpdir))
        try:
            yield TestClient(app)
        finally:
            store.stop_cleanup_scheduler()


class TestHealthCheck:
    """Tests for root health check endpoint."""

    def test_root_returns_healthy_status(self, client: TestClient) -> None:
        """GET / returns healthy status."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "service" in data


class TestGetCases:
    """Tests for GET /api/cases endpoint."""

    def test_returns_list_of_case_ids(self, client: TestClient) -> None:
        """GET /api/cases returns a list of case IDs."""
        with patch("stroke_deepisles_demo.api.routes.list_case_ids") as mock_list:
            mock_list.return_value = ["sub-stroke0001", "sub-stroke0002", "sub-stroke0003"]

            response = client.get("/api/cases")

            assert response.status_code == 200
            data = response.json()
            assert "cases" in data
            assert data["cases"] == ["sub-stroke0001", "sub-stroke0002", "sub-stroke0003"]

    def test_returns_empty_list_when_no_cases(self, client: TestClient) -> None:
        """GET /api/cases returns empty list when no cases available."""
        with patch("stroke_deepisles_demo.api.routes.list_case_ids") as mock_list:
            mock_list.return_value = []

            response = client.get("/api/cases")

            assert response.status_code == 200
            assert response.json()["cases"] == []

    def test_returns_500_on_data_error(self, client: TestClient) -> None:
        """GET /api/cases returns 500 when data layer raises exception."""
        with patch("stroke_deepisles_demo.api.routes.list_case_ids") as mock_list:
            mock_list.side_effect = RuntimeError("Dataset not found")

            response = client.get("/api/cases")

            assert response.status_code == 500
            # Note: Error message is sanitized (doesn't expose internal details)
            assert "Failed to retrieve cases" in response.json()["detail"]


class TestPostSegment:
    """Tests for POST /api/segment endpoint (async job creation)."""

    def test_creates_job_and_returns_202(self, client: TestClient) -> None:
        """POST /api/segment creates a job and returns 202 Accepted."""
        response = client.post(
            "/api/segment",
            json={"case_id": "sub-stroke0001", "fast_mode": True},
        )

        assert response.status_code == 202
        data = response.json()
        assert "jobId" in data
        assert data["status"] == "pending"
        assert "message" in data

    def test_returns_job_id_for_polling(self, client: TestClient) -> None:
        """POST /api/segment returns a job ID that can be used for polling."""
        response = client.post(
            "/api/segment",
            json={"case_id": "sub-stroke0001", "fast_mode": True},
        )

        job_id = response.json()["jobId"]
        assert job_id is not None
        assert len(job_id) > 0

        # Job should be retrievable via GET /api/jobs/{id}
        status_response = client.get(f"/api/jobs/{job_id}")
        assert status_response.status_code == 200

    def test_returns_422_on_missing_case_id(self, client: TestClient) -> None:
        """POST /api/segment returns 422 when case_id is missing."""
        response = client.post("/api/segment", json={})

        assert response.status_code == 422


class TestGetJobStatus:
    """Tests for GET /api/jobs/{job_id} endpoint."""

    def test_returns_pending_job_status(self, client: TestClient) -> None:
        """GET /api/jobs/{id} returns status for a job in the store."""
        from stroke_deepisles_demo.api.job_store import get_job_store

        # Create a job directly in the store (without running inference)
        store = get_job_store()
        store.create_job("pending-job", "sub-stroke0001", fast_mode=True)

        # Get status
        response = client.get("/api/jobs/pending-job")

        assert response.status_code == 200
        data = response.json()
        assert data["jobId"] == "pending-job"
        assert data["status"] == "pending"
        assert "progress" in data
        assert "progressMessage" in data

    def test_returns_404_for_unknown_job(self, client: TestClient) -> None:
        """GET /api/jobs/{id} returns 404 for unknown job ID."""
        response = client.get("/api/jobs/nonexistent-job-id")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_completed_job_includes_result(self, client: TestClient) -> None:
        """GET /api/jobs/{id} includes result data when job is completed."""
        from stroke_deepisles_demo.api.job_store import get_job_store

        # Create and manually complete a job (to avoid waiting for real inference)
        store = get_job_store()
        store.create_job("test-job", "sub-stroke0001", fast_mode=True)
        store.start_job("test-job")
        store.complete_job(
            "test-job",
            {
                "caseId": "sub-stroke0001",
                "diceScore": 0.847,
                "volumeMl": 15.32,
                "elapsedSeconds": 12.5,
                "dwiUrl": "http://localhost/files/test-job/sub-stroke0001/dwi.nii.gz",
                "predictionUrl": "http://localhost/files/test-job/sub-stroke0001/pred.nii.gz",
            },
        )

        response = client.get("/api/jobs/test-job")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["progress"] == 100
        assert data["result"] is not None
        assert data["result"]["caseId"] == "sub-stroke0001"
        assert data["result"]["diceScore"] == 0.847

    def test_failed_job_includes_error(self, client: TestClient) -> None:
        """GET /api/jobs/{id} includes error message when job failed."""
        from stroke_deepisles_demo.api.job_store import get_job_store

        # Create and manually fail a job
        store = get_job_store()
        store.create_job("test-job", "sub-stroke0001", fast_mode=True)
        store.start_job("test-job")
        store.fail_job("test-job", "GPU out of memory")

        response = client.get("/api/jobs/test-job")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert data["error"] == "GPU out of memory"
