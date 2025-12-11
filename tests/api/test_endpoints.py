"""TDD tests for API endpoints.

RED-GREEN-REFACTOR: Tests written FIRST, before implementation.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from stroke_deepisles_demo.api import app


@pytest.fixture
def client() -> TestClient:
    """Create test client for FastAPI app."""
    return TestClient(app)


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
            assert "Dataset not found" in response.json()["detail"]


class TestPostSegment:
    """Tests for POST /api/segment endpoint."""

    def test_runs_segmentation_and_returns_result(self, client: TestClient) -> None:
        """POST /api/segment runs pipeline and returns metrics + URLs."""
        mock_result = MagicMock()
        mock_result.case_id = "sub-stroke0001"
        mock_result.dice_score = 0.847
        mock_result.elapsed_seconds = 12.5
        mock_result.prediction_mask.name = "prediction.nii.gz"
        mock_result.input_files = {"dwi": MagicMock(name="dwi.nii.gz")}
        mock_result.input_files["dwi"].name = "dwi.nii.gz"

        with (
            patch("stroke_deepisles_demo.api.routes.run_pipeline_on_case") as mock_pipeline,
            patch("stroke_deepisles_demo.api.routes.compute_volume_ml") as mock_volume,
        ):
            mock_pipeline.return_value = mock_result
            mock_volume.return_value = 15.32

            response = client.post(
                "/api/segment",
                json={"case_id": "sub-stroke0001", "fast_mode": True},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["caseId"] == "sub-stroke0001"
            assert data["diceScore"] == 0.847
            assert data["volumeMl"] == 15.32
            assert data["elapsedSeconds"] == 12.5
            assert "dwi.nii.gz" in data["dwiUrl"]
            assert "prediction.nii.gz" in data["predictionUrl"]

    def test_passes_fast_mode_to_pipeline(self, client: TestClient) -> None:
        """POST /api/segment passes fast_mode parameter to pipeline."""
        mock_result = MagicMock()
        mock_result.case_id = "sub-stroke0001"
        mock_result.dice_score = None
        mock_result.elapsed_seconds = 45.0
        mock_result.prediction_mask.name = "pred.nii.gz"
        mock_result.input_files = {"dwi": MagicMock()}
        mock_result.input_files["dwi"].name = "dwi.nii.gz"

        with (
            patch("stroke_deepisles_demo.api.routes.run_pipeline_on_case") as mock_pipeline,
            patch("stroke_deepisles_demo.api.routes.compute_volume_ml"),
        ):
            mock_pipeline.return_value = mock_result

            client.post(
                "/api/segment",
                json={"case_id": "sub-stroke0001", "fast_mode": False},
            )

            mock_pipeline.assert_called_once()
            call_kwargs = mock_pipeline.call_args[1]
            assert call_kwargs["fast"] is False

    def test_returns_422_on_missing_case_id(self, client: TestClient) -> None:
        """POST /api/segment returns 422 when case_id is missing."""
        response = client.post("/api/segment", json={})

        assert response.status_code == 422

    def test_returns_500_on_pipeline_error(self, client: TestClient) -> None:
        """POST /api/segment returns 500 when pipeline raises exception."""
        with patch("stroke_deepisles_demo.api.routes.run_pipeline_on_case") as mock_pipeline:
            mock_pipeline.side_effect = RuntimeError("GPU out of memory")

            response = client.post(
                "/api/segment",
                json={"case_id": "sub-stroke0001"},
            )

            assert response.status_code == 500
            assert "GPU out of memory" in response.json()["detail"]
