"""In-memory job store for async ML inference tasks.

This module provides a thread-safe job store for tracking long-running ML inference
jobs. Jobs are stored in-memory, which is appropriate for HuggingFace Spaces since:
1. HF Spaces runs a single uvicorn worker (no multi-worker sync needed)
2. Jobs are ephemeral (results cached, cleanup after TTL)
3. No external dependencies (Redis, DB) required

Note: Multi-worker deployments would require a shared store (Redis/DB).

Architecture:
- Jobs are created with PENDING status
- Background tasks update status to RUNNING, then COMPLETED/FAILED
- Frontend polls GET /api/jobs/{id} for status updates
- Cleanup thread removes old jobs to prevent memory leaks
"""

from __future__ import annotations

import re
import shutil
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING, Any

from stroke_deepisles_demo.api.config import RESULTS_DIR
from stroke_deepisles_demo.core.logging import get_logger

if TYPE_CHECKING:
    from pathlib import Path

logger = get_logger(__name__)

# Regex for safe job IDs (alphanumeric, hyphens, underscores only)
_SAFE_JOB_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")


class JobStatus(str, Enum):
    """Status of an async job."""

    PENDING = "pending"  # Job created, not yet started
    RUNNING = "running"  # Inference in progress
    COMPLETED = "completed"  # Success, results available
    FAILED = "failed"  # Error occurred


@dataclass
class Job:
    """Represents an async segmentation job.

    Attributes:
        id: Unique job identifier (full UUID hex)
        status: Current job status
        case_id: The case being processed
        fast_mode: Whether to use fast inference mode
        created_at: When the job was created
        started_at: When processing began (None if pending)
        completed_at: When processing finished (None if not done)
        progress: Progress percentage (0-100)
        progress_message: Human-readable progress status
        result: Segmentation results (None until completed)
        error: Error message (None unless failed)
    """

    id: str
    status: JobStatus
    case_id: str
    fast_mode: bool
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    progress: int = 0
    progress_message: str = "Queued"
    result: dict[str, Any] | None = None
    error: str | None = None

    @property
    def elapsed_seconds(self) -> float:
        """Calculate elapsed time since job started."""
        if self.started_at is None:
            return 0.0
        end_time = self.completed_at or datetime.now()
        return (end_time - self.started_at).total_seconds()

    def to_dict(self) -> dict[str, Any]:
        """Convert job to dictionary for API response."""
        data: dict[str, Any] = {
            "jobId": self.id,
            "status": self.status.value,
            "progress": self.progress,
            "progressMessage": self.progress_message,
        }

        if self.started_at is not None:
            data["elapsedSeconds"] = round(self.elapsed_seconds, 2)

        if self.status == JobStatus.COMPLETED and self.result is not None:
            data["result"] = self.result

        if self.status == JobStatus.FAILED and self.error is not None:
            data["error"] = self.error

        return data


class JobStore:
    """Thread-safe in-memory job store.

    Provides CRUD operations for jobs with automatic cleanup of old entries.
    Uses a simple dict with a lock for thread safety.

    Usage:
        store = JobStore()
        job = store.create_job("case123", fast_mode=True)
        store.update_progress(job.id, 50, "Processing...")
        store.complete_job(job.id, {"result": "data"})
    """

    # Default time-to-live for completed jobs
    DEFAULT_TTL = timedelta(hours=1)

    # Cleanup interval (how often to check for expired jobs)
    CLEANUP_INTERVAL_SECONDS = 600  # 10 minutes

    def __init__(
        self,
        ttl: timedelta = DEFAULT_TTL,
        results_dir: Path | None = None,
    ) -> None:
        """Initialize the job store.

        Args:
            ttl: How long to keep completed jobs before cleanup
            results_dir: Directory where job results are stored (for cleanup)
        """
        self._jobs: dict[str, Job] = {}
        self._lock = threading.RLock()
        self._ttl = ttl
        self._results_dir = results_dir or RESULTS_DIR
        self._cleanup_thread: threading.Thread | None = None
        self._shutdown = threading.Event()

    @staticmethod
    def _is_safe_job_id(job_id: str) -> bool:
        """Validate job ID to prevent path traversal attacks.

        Only allows alphanumeric characters, hyphens, and underscores.
        """
        return bool(job_id) and _SAFE_JOB_ID_PATTERN.match(job_id) is not None

    def get_active_job_count(self) -> int:
        """Return the number of active (pending or running) jobs.

        Used for concurrency limiting to prevent GPU memory exhaustion.
        """
        with self._lock:
            return sum(
                1
                for job in self._jobs.values()
                if job.status in (JobStatus.PENDING, JobStatus.RUNNING)
            )

    def create_job(self, job_id: str, case_id: str, fast_mode: bool) -> Job:
        """Create a new job in PENDING status.

        Args:
            job_id: Unique identifier for the job
            case_id: Case to process
            fast_mode: Whether to use fast inference

        Returns:
            The created Job object

        Raises:
            ValueError: If job_id is invalid (contains unsafe characters)
            KeyError: If job_id already exists
        """
        if not self._is_safe_job_id(job_id):
            raise ValueError(f"Invalid job_id: {job_id!r}")

        job = Job(
            id=job_id,
            status=JobStatus.PENDING,
            case_id=case_id,
            fast_mode=fast_mode,
            created_at=datetime.now(),
        )
        with self._lock:
            if job_id in self._jobs:
                raise KeyError(f"Job already exists: {job_id}")
            self._jobs[job_id] = job
        # Note: Don't log case_id as it may be sensitive (medical domain)
        logger.info("Created job %s", job_id)
        return job

    def get_job(self, job_id: str) -> Job | None:
        """Get a job by ID.

        Args:
            job_id: The job identifier

        Returns:
            The Job object, or None if not found
        """
        with self._lock:
            return self._jobs.get(job_id)

    def start_job(self, job_id: str) -> None:
        """Mark a job as started (RUNNING status).

        Args:
            job_id: The job identifier
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.status = JobStatus.RUNNING
                job.started_at = datetime.now()
                job.progress = 5
                job.progress_message = "Starting inference..."
                logger.info("Started job %s", job_id)

    def update_progress(
        self,
        job_id: str,
        progress: int,
        message: str,
    ) -> None:
        """Update job progress.

        Args:
            job_id: The job identifier
            progress: Progress percentage (0-100)
            message: Human-readable progress message
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if job and job.status == JobStatus.RUNNING:
                job.progress = min(max(progress, 0), 100)
                job.progress_message = message

    def complete_job(self, job_id: str, result: dict[str, Any]) -> None:
        """Mark a job as successfully completed.

        Args:
            job_id: The job identifier
            result: The segmentation results
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                # Ensure started_at is set for elapsed time calculation
                if job.started_at is None:
                    job.started_at = datetime.now()
                job.status = JobStatus.COMPLETED
                job.completed_at = datetime.now()
                job.progress = 100
                job.progress_message = "Segmentation complete"
                job.result = result
                logger.info(
                    "Completed job %s in %.2fs",
                    job_id,
                    job.elapsed_seconds,
                )

    def fail_job(self, job_id: str, error: str) -> None:
        """Mark a job as failed.

        Args:
            job_id: The job identifier
            error: Error message describing the failure
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                # Ensure started_at is set for elapsed time calculation
                if job.started_at is None:
                    job.started_at = datetime.now()
                job.status = JobStatus.FAILED
                job.completed_at = datetime.now()
                job.progress_message = "Error occurred"
                job.error = error
                logger.error("Failed job %s: %s", job_id, error)

    def cleanup_old_jobs(self) -> int:
        """Remove jobs older than TTL to prevent memory leaks.

        Also cleans up associated result files on disk.

        Returns:
            Number of jobs cleaned up
        """
        now = datetime.now()
        expired_ids: list[str] = []

        with self._lock:
            for job_id, job in self._jobs.items():
                if job.completed_at and (now - job.completed_at) > self._ttl:
                    expired_ids.append(job_id)

            for job_id in expired_ids:
                del self._jobs[job_id]

        # Clean up result files outside the lock
        # Use path validation to prevent path traversal attacks
        base_dir = self._results_dir.resolve()
        for job_id in expired_ids:
            # Skip cleanup for unsafe job IDs (shouldn't happen, but defense in depth)
            if not self._is_safe_job_id(job_id):
                logger.warning("Skipping cleanup for unsafe job id %r", job_id)
                continue

            result_dir = (self._results_dir / job_id).resolve()
            # Verify path is within results directory (prevent traversal)
            if not result_dir.is_relative_to(base_dir):
                logger.warning("Path traversal attempt blocked for job %s", job_id)
                continue

            if result_dir.exists():
                try:
                    shutil.rmtree(result_dir)
                    logger.debug("Cleaned up result files for job %s", job_id)
                except OSError as e:
                    logger.warning("Failed to cleanup %s: %s", result_dir, e)

        if expired_ids:
            logger.info("Cleaned up %d expired jobs", len(expired_ids))

        return len(expired_ids)

    def start_cleanup_scheduler(self) -> None:
        """Start background thread for periodic job cleanup."""
        if self._cleanup_thread is not None:
            return  # Already running

        def cleanup_loop() -> None:
            while not self._shutdown.wait(self.CLEANUP_INTERVAL_SECONDS):
                try:
                    self.cleanup_old_jobs()
                except Exception:
                    logger.exception("Error during job cleanup")

        self._cleanup_thread = threading.Thread(
            target=cleanup_loop,
            daemon=True,
            name="job-cleanup",
        )
        self._cleanup_thread.start()
        logger.info("Started job cleanup scheduler (interval=%ds)", self.CLEANUP_INTERVAL_SECONDS)

    def stop_cleanup_scheduler(self) -> None:
        """Stop the cleanup scheduler thread."""
        self._shutdown.set()
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=5)
            self._cleanup_thread = None
        logger.info("Stopped job cleanup scheduler")

    def __len__(self) -> int:
        """Return number of jobs in store."""
        with self._lock:
            return len(self._jobs)


# Global job store instance
# Initialized in main.py on app startup
job_store: JobStore | None = None


def get_job_store() -> JobStore:
    """Get the global job store instance.

    Raises:
        RuntimeError: If job store not initialized
    """
    if job_store is None:
        raise RuntimeError("Job store not initialized. Call init_job_store() first.")
    return job_store


def init_job_store(results_dir: Path | None = None) -> JobStore:
    """Initialize the global job store.

    Args:
        results_dir: Directory for job results

    Returns:
        The initialized JobStore
    """
    global job_store
    job_store = JobStore(results_dir=results_dir)
    job_store.start_cleanup_scheduler()
    return job_store
