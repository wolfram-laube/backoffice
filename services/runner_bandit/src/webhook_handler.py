"""FastAPI webhook handler for GitLab events + MAB API.

v0.3.0: Availability-aware recommendations + GCP VM auto-start/stop.
"""
import os
import logging
from typing import Optional, List
from fastapi import FastAPI, Request, HTTPException, Header
from pydantic import BaseModel

from .bandit import (
    UCB1Bandit, ThompsonSamplingBandit,
    calculate_reward, create_backend
)
from .availability import (
    check_runner_availability, start_gcp_vm, stop_gcp_vm,
    get_gcp_vm_status, GCP_RUNNERS
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Runner Bandit Service",
    description="Intelligent CI Runner Selection using Multi-Armed Bandits",
    version="0.3.0"
)

# Configuration
RUNNERS = [
    "gitlab-runner-nordic",
    "Mac Docker Runner",
    "Mac2 Docker Runner",
    "Linux Yoga Docker Runner",
    "Mac K8s Runner",
    "Mac2 K8s Runner",
]

RUNNER_COSTS = {  # EUR/hour
    "gitlab-runner-nordic": 0.02,
    "Mac Docker Runner": 0.0,
    "Mac2 Docker Runner": 0.0,
    "Linux Yoga Docker Runner": 0.0,
    "Mac K8s Runner": 0.0,
    "Mac2 K8s Runner": 0.0,
}

RUNNER_TAG_MAP = {
    "gitlab-runner-nordic": "nordic",
    "Mac Docker Runner": "mac-docker",
    "Mac2 Docker Runner": "mac2-docker",
    "Linux Yoga Docker Runner": "linux-docker",
    "Mac K8s Runner": "mac-k8s",
    "Mac2 K8s Runner": "mac2-k8s",
}

ALGORITHM = os.getenv("BANDIT_ALGORITHM", "ucb1")
WEBHOOK_SECRET = os.getenv("GITLAB_WEBHOOK_SECRET", "")
GITLAB_TOKEN = os.getenv("GITLAB_API_TOKEN", "")

# Initialize bandit
backend = create_backend()
if ALGORITHM == "thompson":
    bandit = ThompsonSamplingBandit(RUNNERS, backend=backend)
else:
    bandit = UCB1Bandit(RUNNERS, c=2.0, backend=backend)


# ---- Models ----
class RecommendationResponse(BaseModel):
    recommended_runner: str
    recommended_tag: str
    algorithm: str
    total_observations: int
    availability_checked: bool
    online_runners: List[str]
    gcp_auto_started: bool
    exploration_info: dict


class UpdateRequest(BaseModel):
    runner: str
    success: bool
    duration: float
    job_name: Optional[str] = None
    project: Optional[str] = None


# ---- Endpoints ----
@app.get("/")
async def root():
    return {
        "service": "Runner Bandit",
        "version": "0.3.0",
        "algorithm": bandit.__class__.__name__,
        "total_observations": bandit.total_pulls,
        "runners": list(RUNNERS),
        "persistence": "gcs" if os.getenv("BANDIT_GCS_BUCKET") else "local",
        "features": ["availability-check", "gcp-auto-start", "gcp-auto-stop"]
    }


@app.get("/recommend", response_model=RecommendationResponse)
async def recommend_runner(
    job_type: str = "default",
    check_availability: bool = True,
    auto_start_gcp: bool = True,
):
    """Get runner recommendation based on MAB policy + availability.

    Flow:
      1. Check which runners are online (GitLab API)
      2. If none → auto-start GCP VM (if enabled)
      3. MAB selects from online runners only
      4. Fallback to docker-any if everything fails
    """
    gcp_started = False
    online_runners = list(RUNNERS)  # Assume all if no check

    if check_availability and GITLAB_TOKEN:
        avail = check_runner_availability(GITLAB_TOKEN)
        online_runners = avail.online_runners

        if not online_runners:
            logger.warning("No runners online!")

            if auto_start_gcp:
                logger.info("Attempting GCP VM auto-start...")
                success, msg = start_gcp_vm()
                gcp_started = success
                logger.info(f"GCP auto-start: {msg}")

                if success:
                    # Nordic will come online in ~30-60s
                    # For now, recommend it optimistically
                    online_runners = ["gitlab-runner-nordic"]

            if not online_runners:
                # Total fallback
                return RecommendationResponse(
                    recommended_runner="fallback",
                    recommended_tag="docker-any",
                    algorithm=bandit.__class__.__name__,
                    total_observations=bandit.total_pulls,
                    availability_checked=True,
                    online_runners=[],
                    gcp_auto_started=gcp_started,
                    exploration_info=bandit.get_stats()
                )

    # MAB selects from available runners only
    # Temporarily filter bandit to online runners
    original_runners = bandit.runners
    bandit.runners = [r for r in original_runners if r in online_runners]

    if not bandit.runners:
        bandit.runners = original_runners
        runner = bandit.select_runner()
    else:
        runner = bandit.select_runner()

    bandit.runners = original_runners  # Restore

    tag = RUNNER_TAG_MAP.get(runner, "docker-any")

    return RecommendationResponse(
        recommended_runner=runner,
        recommended_tag=tag,
        algorithm=bandit.__class__.__name__,
        total_observations=bandit.total_pulls,
        availability_checked=check_availability and bool(GITLAB_TOKEN),
        online_runners=online_runners,
        gcp_auto_started=gcp_started,
        exploration_info=bandit.get_stats()
    )


@app.post("/update")
async def update_observation(request: UpdateRequest):
    """Update bandit with job outcome."""
    if request.runner not in RUNNERS:
        raise HTTPException(status_code=400, detail=f"Unknown runner: {request.runner}")

    cost = RUNNER_COSTS.get(request.runner, 0.0)
    reward = calculate_reward(request.success, request.duration, cost)
    bandit.update(request.runner, reward, request.success, request.duration)

    logger.info(
        f"Updated {request.runner}: success={request.success}, "
        f"duration={request.duration:.1f}s, reward={reward:.4f}, "
        f"job={request.job_name}, project={request.project}"
    )
    return {
        "status": "updated",
        "runner": request.runner,
        "reward": round(reward, 4),
        "total_observations": bandit.total_pulls
    }


@app.post("/webhooks/gitlab")
async def handle_gitlab_webhook(
    request: Request,
    x_gitlab_token: Optional[str] = Header(None)
):
    """Handle GitLab webhook events (job completion)."""
    if WEBHOOK_SECRET and x_gitlab_token != WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid webhook token")

    payload = await request.json()
    object_kind = payload.get("object_kind")

    if object_kind == "build":
        return await _handle_build_event(payload)
    return {"status": "ignored", "reason": f"Unhandled: {object_kind}"}


async def _handle_build_event(payload: dict):
    """Process build (job) events."""
    status = payload.get("build_status")
    if status not in ["success", "failed"]:
        return {"status": "ignored", "reason": f"Status: {status}"}

    runner_info = payload.get("runner")
    if not runner_info:
        return {"status": "ignored", "reason": "No runner info"}

    runner_name = runner_info.get("description", "unknown")
    duration = payload.get("build_duration", 0)

    if runner_name not in RUNNERS:
        return {"status": "ignored", "reason": f"Unknown runner: {runner_name}"}

    success = status == "success"
    cost = RUNNER_COSTS.get(runner_name, 0.0)
    reward = calculate_reward(success, duration, cost)
    bandit.update(runner_name, reward, success, duration)

    logger.info(
        f"Webhook: {runner_name} | {status} | {duration:.1f}s | reward={reward:.4f}"
    )
    return {
        "status": "updated",
        "runner": runner_name,
        "build_status": status,
        "reward": round(reward, 4),
        "total_observations": bandit.total_pulls
    }


# ---- Availability & VM Control ----

@app.get("/availability")
async def get_availability():
    """Check which runners are online right now."""
    if not GITLAB_TOKEN:
        return {"error": "GITLAB_API_TOKEN not configured", "runners": []}

    avail = check_runner_availability(GITLAB_TOKEN)
    return {
        "online": avail.online_runners,
        "offline": avail.offline_runners,
        "online_count": len(avail.online_runners),
        "offline_count": len(avail.offline_runners),
    }


@app.post("/vm/start")
async def vm_start():
    """Manually start the GCP VM."""
    success, msg = start_gcp_vm()
    return {"success": success, "message": msg}


@app.post("/vm/stop")
async def vm_stop():
    """Manually stop the GCP VM (save costs)."""
    success, msg = stop_gcp_vm()
    return {"success": success, "message": msg}


@app.get("/vm/status")
async def vm_status():
    """Get GCP VM status."""
    status = get_gcp_vm_status()
    return {"instance": "gitlab-runner-nordic", "status": status}


# ---- Stats & Admin ----

@app.get("/stats")
async def get_statistics():
    """Detailed statistics for all runners."""
    stats = bandit.get_stats()
    return {
        "algorithm": bandit.__class__.__name__,
        "total_observations": bandit.total_pulls,
        "persistence": "gcs" if os.getenv("BANDIT_GCS_BUCKET") else "local",
        "runners": stats,
        "ranking": sorted(
            stats.keys(),
            key=lambda r: stats[r]["mean_reward"],
            reverse=True
        )
    }


@app.post("/reset")
async def reset_bandit():
    """Reset all statistics."""
    global bandit
    new_backend = create_backend()
    if ALGORITHM == "thompson":
        bandit = ThompsonSamplingBandit(RUNNERS, backend=new_backend)
    else:
        bandit = UCB1Bandit(RUNNERS, c=2.0, backend=new_backend)
    bandit._save_state()
    return {"status": "reset", "algorithm": bandit.__class__.__name__}


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "healthy", "observations": bandit.total_pulls}
