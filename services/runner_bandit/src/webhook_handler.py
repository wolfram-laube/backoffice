"""FastAPI webhook handler for GitLab events + MAB API."""
import os
import logging
from typing import Optional
from fastapi import FastAPI, Request, HTTPException, Header
from pydantic import BaseModel

from .bandit import (
    UCB1Bandit, ThompsonSamplingBandit,
    calculate_reward, create_backend
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Runner Bandit Service",
    description="Intelligent CI Runner Selection using Multi-Armed Bandits",
    version="0.2.0"
)

# Configuration
RUNNERS = [
    "gitlab-runner-nordic",
    "Mac Docker Runner",
    "Mac2 Docker Runner",
    "Linux Yoga Docker Runner"
]

RUNNER_COSTS = {  # EUR/hour
    "gitlab-runner-nordic": 0.02,
    "Mac Docker Runner": 0.0,
    "Mac2 Docker Runner": 0.0,
    "Linux Yoga Docker Runner": 0.0,
}

# Runner name → GitLab CI tag mapping
RUNNER_TAG_MAP = {
    "gitlab-runner-nordic": "nordic",
    "Mac Docker Runner": "mac-docker",
    "Mac2 Docker Runner": "mac2-docker",
    "Linux Yoga Docker Runner": "linux-docker",
}

ALGORITHM = os.getenv("BANDIT_ALGORITHM", "ucb1")
WEBHOOK_SECRET = os.getenv("GITLAB_WEBHOOK_SECRET", "")

# Initialize bandit with auto-detected backend (GCS or local)
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
        "version": "0.2.0",
        "algorithm": bandit.__class__.__name__,
        "total_observations": bandit.total_pulls,
        "runners": list(RUNNERS),
        "persistence": "gcs" if os.getenv("BANDIT_GCS_BUCKET") else "local"
    }


@app.get("/recommend", response_model=RecommendationResponse)
async def recommend_runner(job_type: str = "default"):
    """Get runner recommendation based on MAB policy."""
    runner = bandit.select_runner()
    tag = RUNNER_TAG_MAP.get(runner, "docker-any")

    return RecommendationResponse(
        recommended_runner=runner,
        recommended_tag=tag,
        algorithm=bandit.__class__.__name__,
        total_observations=bandit.total_pulls,
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

    return {"status": "ignored", "reason": f"Unhandled event type: {object_kind}"}


async def _handle_build_event(payload: dict):
    """Process build (job) events from GitLab webhook."""
    status = payload.get("build_status")

    if status not in ["success", "failed"]:
        return {"status": "ignored", "reason": f"Build status: {status}"}

    runner_info = payload.get("runner")
    if not runner_info:
        return {"status": "ignored", "reason": "No runner info"}

    runner_name = runner_info.get("description", "unknown")
    duration = payload.get("build_duration", 0)
    job_name = payload.get("build_name", "unknown")
    project = payload.get("project_name", "unknown")

    if runner_name not in RUNNERS:
        logger.warning(f"Unknown runner in webhook: {runner_name}")
        return {"status": "ignored", "reason": f"Unknown runner: {runner_name}"}

    success = status == "success"
    cost = RUNNER_COSTS.get(runner_name, 0.0)
    reward = calculate_reward(success, duration, cost)

    bandit.update(runner_name, reward, success, duration)

    logger.info(
        f"Webhook: {runner_name} | {status} | {duration:.1f}s | "
        f"reward={reward:.4f} | job={job_name} | project={project}"
    )

    return {
        "status": "updated",
        "runner": runner_name,
        "build_status": status,
        "reward": round(reward, 4),
        "total_observations": bandit.total_pulls
    }


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
    # Save empty state to clear GCS
    bandit._save_state()
    return {"status": "reset", "algorithm": bandit.__class__.__name__}


@app.get("/health")
async def health():
    """Health check for monitoring."""
    return {"status": "healthy", "observations": bandit.total_pulls}
