"""Unit tests for the async job store.

Tests the JobStore class that manages background ML inference jobs.
Follows Uncle Bob's testing principles:
- Test behavior, not implementation
- Each test verifies one thing
- Tests are independent and repeatable
"""

from collections.abc import Generator
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pytest

from stroke_deepisles_demo.api.job_store import (
    Job,
    JobStatus,
    JobStore,
    get_job_store,
    init_job_store,
)


class TestJob:
    """Tests for the Job dataclass."""

    def test_new_job_has_zero_elapsed_seconds(self) -> None:
        """A job that hasn't started should report 0 elapsed seconds."""
        job = Job(
            id="abc123",
            status=JobStatus.PENDING,
            case_id="sub-stroke0001",
            fast_mode=True,
            created_at=datetime.now(),
        )

        assert job.elapsed_seconds == 0.0

    def test_running_job_tracks_elapsed_time(self) -> None:
        """A running job should report elapsed time since start."""
        start = datetime.now() - timedelta(seconds=10)
        job = Job(
            id="abc123",
            status=JobStatus.RUNNING,
            case_id="sub-stroke0001",
            fast_mode=True,
            created_at=start - timedelta(seconds=1),
            started_at=start,
        )

        # Should be approximately 10 seconds (with some tolerance)
        assert 9.5 <= job.elapsed_seconds <= 11.0

    def test_completed_job_has_fixed_elapsed_time(self) -> None:
        """A completed job should report time from start to completion."""
        start = datetime.now() - timedelta(seconds=30)
        end = start + timedelta(seconds=15)
        job = Job(
            id="abc123",
            status=JobStatus.COMPLETED,
            case_id="sub-stroke0001",
            fast_mode=True,
            created_at=start - timedelta(seconds=1),
            started_at=start,
            completed_at=end,
        )

        # Should be exactly 15 seconds (completed job doesn't change)
        assert job.elapsed_seconds == 15.0

    def test_to_dict_includes_required_fields(self) -> None:
        """Job.to_dict() should include all fields needed by the API."""
        job = Job(
            id="abc123",
            status=JobStatus.RUNNING,
            case_id="sub-stroke0001",
            fast_mode=True,
            created_at=datetime.now(),
            started_at=datetime.now(),
            progress=50,
            progress_message="Processing...",
        )

        data = job.to_dict()

        assert data["jobId"] == "abc123"
        assert data["status"] == "running"
        assert data["progress"] == 50
        assert data["progressMessage"] == "Processing..."
        assert "elapsedSeconds" in data

    def test_to_dict_includes_result_when_completed(self) -> None:
        """Completed jobs should include result data in to_dict()."""
        job = Job(
            id="abc123",
            status=JobStatus.COMPLETED,
            case_id="sub-stroke0001",
            fast_mode=True,
            created_at=datetime.now(),
            started_at=datetime.now(),
            completed_at=datetime.now(),
            result={"caseId": "sub-stroke0001", "diceScore": 0.847},
        )

        data = job.to_dict()

        assert "result" in data
        assert data["result"]["diceScore"] == 0.847

    def test_to_dict_includes_error_when_failed(self) -> None:
        """Failed jobs should include error message in to_dict()."""
        job = Job(
            id="abc123",
            status=JobStatus.FAILED,
            case_id="sub-stroke0001",
            fast_mode=True,
            created_at=datetime.now(),
            error="GPU out of memory",
        )

        data = job.to_dict()

        assert "error" in data
        assert data["error"] == "GPU out of memory"


class TestJobStore:
    """Tests for the JobStore class."""

    @pytest.fixture
    def store(self) -> Generator[JobStore, None, None]:
        """Create a fresh JobStore for each test."""
        with TemporaryDirectory() as tmpdir:
            yield JobStore(results_dir=Path(tmpdir))

    def test_create_job_returns_pending_job(self, store: JobStore) -> None:
        """Creating a job should return a job in PENDING status."""
        job = store.create_job("job-1", "sub-stroke0001", fast_mode=True)

        assert job.id == "job-1"
        assert job.status == JobStatus.PENDING
        assert job.case_id == "sub-stroke0001"
        assert job.fast_mode is True

    def test_get_job_returns_created_job(self, store: JobStore) -> None:
        """get_job() should return a previously created job."""
        store.create_job("job-1", "sub-stroke0001", fast_mode=True)

        job = store.get_job("job-1")

        assert job is not None
        assert job.id == "job-1"

    def test_get_job_returns_none_for_unknown_id(self, store: JobStore) -> None:
        """get_job() should return None for unknown job IDs."""
        job = store.get_job("nonexistent")

        assert job is None

    def test_start_job_changes_status_to_running(self, store: JobStore) -> None:
        """start_job() should update job status to RUNNING."""
        store.create_job("job-1", "sub-stroke0001", fast_mode=True)

        store.start_job("job-1")

        job = store.get_job("job-1")
        assert job is not None
        assert job.status == JobStatus.RUNNING
        assert job.started_at is not None

    def test_update_progress_changes_progress_fields(self, store: JobStore) -> None:
        """update_progress() should update progress and message."""
        store.create_job("job-1", "sub-stroke0001", fast_mode=True)
        store.start_job("job-1")

        store.update_progress("job-1", 75, "Computing metrics...")

        job = store.get_job("job-1")
        assert job is not None
        assert job.progress == 75
        assert job.progress_message == "Computing metrics..."

    def test_update_progress_clamps_to_valid_range(self, store: JobStore) -> None:
        """update_progress() should clamp progress to 0-100."""
        store.create_job("job-1", "sub-stroke0001", fast_mode=True)
        store.start_job("job-1")

        store.update_progress("job-1", 150, "Over 100")
        job = store.get_job("job-1")
        assert job is not None
        assert job.progress == 100

        store.update_progress("job-1", -10, "Negative")
        job = store.get_job("job-1")
        assert job is not None
        assert job.progress == 0

    def test_complete_job_sets_status_and_result(self, store: JobStore) -> None:
        """complete_job() should mark job as completed with result."""
        store.create_job("job-1", "sub-stroke0001", fast_mode=True)
        store.start_job("job-1")

        result = {"caseId": "sub-stroke0001", "diceScore": 0.847}
        store.complete_job("job-1", result)

        job = store.get_job("job-1")
        assert job is not None
        assert job.status == JobStatus.COMPLETED
        assert job.progress == 100
        assert job.result == result
        assert job.completed_at is not None

    def test_fail_job_sets_status_and_error(self, store: JobStore) -> None:
        """fail_job() should mark job as failed with error message."""
        store.create_job("job-1", "sub-stroke0001", fast_mode=True)
        store.start_job("job-1")

        store.fail_job("job-1", "GPU out of memory")

        job = store.get_job("job-1")
        assert job is not None
        assert job.status == JobStatus.FAILED
        assert job.error == "GPU out of memory"
        assert job.completed_at is not None

    def test_len_returns_number_of_jobs(self, store: JobStore) -> None:
        """len(store) should return the number of jobs."""
        assert len(store) == 0

        store.create_job("job-1", "case1", fast_mode=True)
        assert len(store) == 1

        store.create_job("job-2", "case2", fast_mode=True)
        assert len(store) == 2


class TestJobStoreCleanup:
    """Tests for job cleanup functionality."""

    def test_cleanup_removes_old_completed_jobs(self) -> None:
        """cleanup_old_jobs() should remove jobs older than TTL."""
        with TemporaryDirectory() as tmpdir:
            # Use a very short TTL for testing
            store = JobStore(ttl=timedelta(seconds=0), results_dir=Path(tmpdir))

            store.create_job("job-1", "case1", fast_mode=True)
            store.start_job("job-1")
            store.complete_job("job-1", {"result": "data"})

            # Job is "old" immediately (TTL=0)
            cleaned = store.cleanup_old_jobs()

            assert cleaned == 1
            assert store.get_job("job-1") is None

    def test_cleanup_keeps_running_jobs(self) -> None:
        """cleanup_old_jobs() should not remove running jobs."""
        with TemporaryDirectory() as tmpdir:
            store = JobStore(ttl=timedelta(seconds=0), results_dir=Path(tmpdir))

            store.create_job("job-1", "case1", fast_mode=True)
            store.start_job("job-1")
            # Job is running, not completed

            cleaned = store.cleanup_old_jobs()

            assert cleaned == 0
            assert store.get_job("job-1") is not None

    def test_cleanup_removes_result_files(self) -> None:
        """cleanup_old_jobs() should also remove result files on disk."""
        with TemporaryDirectory() as tmpdir:
            results_dir = Path(tmpdir)
            store = JobStore(ttl=timedelta(seconds=0), results_dir=results_dir)

            # Create job and its result directory
            store.create_job("job-1", "case1", fast_mode=True)
            store.start_job("job-1")
            job_results = results_dir / "job-1"
            job_results.mkdir()
            (job_results / "prediction.nii.gz").touch()
            store.complete_job("job-1", {"result": "data"})

            # Cleanup should remove both job record and files
            store.cleanup_old_jobs()

            assert not job_results.exists()


class TestGlobalJobStore:
    """Tests for the global job store singleton."""

    def test_get_job_store_raises_before_init(self) -> None:
        """get_job_store() should raise if not initialized."""
        # Patch the global to simulate uninitialized state
        with (
            patch("stroke_deepisles_demo.api.job_store.job_store", None),
            pytest.raises(RuntimeError, match="not initialized"),
        ):
            get_job_store()

    def test_init_job_store_creates_global_instance(self) -> None:
        """init_job_store() should create and return a JobStore."""
        with TemporaryDirectory() as tmpdir:
            store = init_job_store(results_dir=Path(tmpdir))

            assert store is not None
            assert isinstance(store, JobStore)

            # Clean up the scheduler
            store.stop_cleanup_scheduler()
