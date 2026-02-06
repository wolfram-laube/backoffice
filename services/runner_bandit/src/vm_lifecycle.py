"""GCP VM lifecycle management for MAB-triggered auto-start.

Tracks whether the MAB service started the VM and shuts it down
after a configurable idle period with no jobs running.
"""
import os
import time
import json
import logging
import threading
from typing import Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

IDLE_SHUTDOWN_SECONDS = int(os.getenv("GCP_IDLE_SHUTDOWN_SECONDS", "300"))  # 5 min default


@dataclass
class VMLifecycle:
    """Tracks VM state for auto-stop after MAB-triggered start."""
    auto_started: bool = False
    started_at: Optional[float] = None
    last_job_finished_at: Optional[float] = None
    active_jobs: int = 0  # rough counter from webhooks
    _shutdown_timer: Optional[threading.Timer] = field(default=None, repr=False)

    def record_auto_start(self):
        """Called when /recommend triggers a VM start."""
        self.auto_started = True
        self.started_at = time.time()
        self.active_jobs = 0
        self.last_job_finished_at = None
        logger.info(f"VM auto-start recorded. Will auto-stop after {IDLE_SHUTDOWN_SECONDS}s idle.")

    def record_job_started(self, runner: str):
        """Called when a job begins on GCP runner (from webhook)."""
        if self._is_gcp_runner(runner):
            self.active_jobs = max(0, self.active_jobs) + 1
            self._cancel_shutdown()
            logger.info(f"GCP job started. Active: ~{self.active_jobs}")

    def record_job_finished(self, runner: str) -> bool:
        """Called when a job finishes on GCP runner.

        Returns True if VM shutdown was scheduled.
        """
        if not self._is_gcp_runner(runner):
            return False

        self.active_jobs = max(0, self.active_jobs - 1)
        self.last_job_finished_at = time.time()

        if not self.auto_started:
            logger.info("VM was not auto-started by MAB, skipping auto-stop")
            return False

        if self.active_jobs <= 0:
            logger.info(
                f"Last GCP job finished. Scheduling shutdown in {IDLE_SHUTDOWN_SECONDS}s "
                f"(cancels if new job arrives)"
            )
            self._schedule_shutdown()
            return True

        logger.info(f"GCP job finished. Still ~{self.active_jobs} active, no shutdown yet.")
        return False

    def reset(self):
        """Reset after VM stop."""
        self._cancel_shutdown()
        self.auto_started = False
        self.started_at = None
        self.last_job_finished_at = None
        self.active_jobs = 0

    def _schedule_shutdown(self):
        """Schedule VM shutdown after idle period."""
        self._cancel_shutdown()

        def _do_shutdown():
            if self.active_jobs > 0:
                logger.info("New jobs appeared, aborting shutdown")
                return
            logger.info("Idle timeout reached — stopping GCP VM")
            try:
                from .availability import stop_gcp_vm
                success, msg = stop_gcp_vm()
                logger.info(f"VM stop result: {success} — {msg}")
                if success:
                    self.reset()
            except Exception as e:
                logger.error(f"Failed to stop VM: {e}")

        self._shutdown_timer = threading.Timer(IDLE_SHUTDOWN_SECONDS, _do_shutdown)
        self._shutdown_timer.daemon = True
        self._shutdown_timer.start()
        logger.info(f"Shutdown timer set: {IDLE_SHUTDOWN_SECONDS}s")

    def _cancel_shutdown(self):
        """Cancel pending shutdown (new job arrived)."""
        if self._shutdown_timer and self._shutdown_timer.is_alive():
            self._shutdown_timer.cancel()
            logger.info("Shutdown timer cancelled (new activity)")
        self._shutdown_timer = None

    def _is_gcp_runner(self, runner: str) -> bool:
        from .availability import GCP_RUNNERS
        return runner in GCP_RUNNERS

    def status(self) -> dict:
        return {
            "auto_started": self.auto_started,
            "started_at": self.started_at,
            "idle_shutdown_seconds": IDLE_SHUTDOWN_SECONDS,
            "active_gcp_jobs": self.active_jobs,
            "shutdown_pending": bool(
                self._shutdown_timer and self._shutdown_timer.is_alive()
            ),
            "seconds_since_last_job": (
                round(time.time() - self.last_job_finished_at, 1)
                if self.last_job_finished_at else None
            ),
        }


# Singleton
vm_lifecycle = VMLifecycle()
