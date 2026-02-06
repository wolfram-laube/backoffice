"""Runner availability checker via GitLab API.

Checks which runners are actually online before MAB makes a recommendation.
If no runners are available, can trigger GCP VM auto-start.
"""
import os
import logging
import json
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Runner ID → name mapping (for GitLab API lookup)
RUNNER_REGISTRY = {
    51608579: "gitlab-runner-nordic",
    51336735: "Mac Docker Runner",
    51337424: "Mac2 Docker Runner",
    51337426: "Linux Yoga Docker Runner",
    51336736: "Mac K8s Runner",
    51337457: "Mac2 K8s Runner",
}

# Which runners need the GCP VM?
GCP_RUNNERS = {"gitlab-runner-nordic"}

# GCP VM config
GCP_PROJECT = os.getenv("GCP_PROJECT", "myk8sproject-207017")
GCP_ZONE = os.getenv("GCP_ZONE", "europe-north2-a")
GCP_INSTANCE = os.getenv("GCP_INSTANCE", "gitlab-runner-nordic")


@dataclass
class AvailabilityResult:
    online_runners: List[str]
    offline_runners: List[str]
    gcp_vm_status: Optional[str] = None  # RUNNING, TERMINATED, etc.
    gcp_started: bool = False


def check_runner_availability(gitlab_token: Optional[str] = None) -> AvailabilityResult:
    """Check which runners are currently online via GitLab API."""
    token = gitlab_token or os.getenv("GITLAB_API_TOKEN")
    if not token:
        logger.warning("No GitLab API token — assuming all runners available")
        return AvailabilityResult(
            online_runners=list(RUNNER_REGISTRY.values()),
            offline_runners=[]
        )

    import urllib.request

    online = []
    offline = []

    for runner_id, runner_name in RUNNER_REGISTRY.items():
        try:
            req = urllib.request.Request(
                f"https://gitlab.com/api/v4/runners/{runner_id}",
                headers={"PRIVATE-TOKEN": token}
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
                if data.get("status") == "online":
                    online.append(runner_name)
                else:
                    offline.append(runner_name)
        except Exception as e:
            logger.warning(f"Could not check runner {runner_name}: {e}")
            offline.append(runner_name)

    logger.info(f"Runner availability: {len(online)} online, {len(offline)} offline")
    return AvailabilityResult(online_runners=online, offline_runners=offline)


def start_gcp_vm() -> Tuple[bool, str]:
    """Start the GCP VM if it's not running. Returns (success, message)."""
    try:
        from google.cloud import compute_v1
    except ImportError:
        return False, "google-cloud-compute not installed"

    try:
        client = compute_v1.InstancesClient()

        # Check current status
        instance = client.get(
            project=GCP_PROJECT,
            zone=GCP_ZONE,
            instance=GCP_INSTANCE
        )

        if instance.status == "RUNNING":
            return True, f"VM {GCP_INSTANCE} already running"

        if instance.status in ("TERMINATED", "STOPPED"):
            logger.info(f"Starting GCP VM {GCP_INSTANCE}...")
            operation = client.start(
                project=GCP_PROJECT,
                zone=GCP_ZONE,
                instance=GCP_INSTANCE
            )
            # Don't wait for completion — it takes ~30s
            return True, f"VM {GCP_INSTANCE} start initiated (was {instance.status})"

        return False, f"VM in unexpected state: {instance.status}"

    except Exception as e:
        logger.error(f"Failed to start GCP VM: {e}")
        return False, str(e)


def get_gcp_vm_status() -> str:
    """Get current GCP VM status."""
    try:
        from google.cloud import compute_v1
        client = compute_v1.InstancesClient()
        instance = client.get(
            project=GCP_PROJECT,
            zone=GCP_ZONE,
            instance=GCP_INSTANCE
        )
        return instance.status
    except Exception as e:
        return f"UNKNOWN ({e})"


def stop_gcp_vm() -> Tuple[bool, str]:
    """Stop the GCP VM to save costs."""
    try:
        from google.cloud import compute_v1
        client = compute_v1.InstancesClient()

        instance = client.get(
            project=GCP_PROJECT,
            zone=GCP_ZONE,
            instance=GCP_INSTANCE
        )

        if instance.status in ("TERMINATED", "STOPPED"):
            return True, f"VM {GCP_INSTANCE} already stopped"

        if instance.status == "RUNNING":
            client.stop(
                project=GCP_PROJECT,
                zone=GCP_ZONE,
                instance=GCP_INSTANCE
            )
            return True, f"VM {GCP_INSTANCE} stop initiated"

        return False, f"VM in unexpected state: {instance.status}"

    except Exception as e:
        return False, str(e)
