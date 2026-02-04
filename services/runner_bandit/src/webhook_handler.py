"""FastAPI webhook handler for GitLab events."""
import os
import logging
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, Request, HTTPException, Header
from pydantic import BaseModel

from .bandit import UCB1Bandit, ThompsonSamplingBandit, calculate_reward

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Runner Bandit Service",
    description="Intelligent CI Runner Selection using Multi-Armed Bandits",
    version="0.1.0"
)

# Configuration
RUNNERS = [
    "gitlab-runner-nordic",
    "Mac Docker Runner", 
    "Mac2 Docker Runner",
    "Linux Yoga Docker Runner"
]

RUNNER_COSTS = {  # EUR/hour
    "gitlab-runner-nordic": 0.02,  # GCP e2-small preemptible
    "Mac Docker Runner": 0.0,
    "Mac2 Docker Runner": 0.0,
    "Linux Yoga Docker Runner": 0.0,
}

STATE_FILE = Path(os.getenv("BANDIT_STATE_FILE", "/tmp/bandit_state.json"))
ALGORITHM = os.getenv("BANDIT_ALGORITHM", "ucb1")
WEBHOOK_SECRET = os.getenv("GITLAB_WEBHOOK_SECRET", "")

# Initialize bandit
if ALGORITHM == "thompson":
    bandit = ThompsonSamplingBandit(RUNNERS)
else:
    bandit = UCB1Bandit(RUNNERS, c=2.0)

# Load persisted state
bandit.load_state(STATE_FILE)


class RecommendationResponse(BaseModel):
    recommended_runner: str
    algorithm: str
    exploration_info: dict


class UpdateRequest(BaseModel):
    runner: str
    success: bool
    duration: float
    job_name: Optional[str] = None


@app.get("/")
async def root():
    return {
        "service": "Runner Bandit",
        "algorithm": bandit.__class__.__name__,
        "total_observations": bandit.total_pulls,
        "runners": list(RUNNERS)
    }


@app.get("/recommend", response_model=RecommendationResponse)
async def recommend_runner(job_type: str = "default"):
    """Get runner recommendation based on MAB policy."""
    runner = bandit.select_runner()
    
    return RecommendationResponse(
        recommended_runner=runner,
        algorithm=bandit.__class__.__name__,
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
    bandit.save_state(STATE_FILE)
    
    logger.info(f"Updated {request.runner}: success={request.success}, "
                f"duration={request.duration:.1f}s, reward={reward:.4f}")
    
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
    """Handle GitLab webhook events."""
    # Verify webhook secret
    if WEBHOOK_SECRET and x_gitlab_token != WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid webhook token")
    
    payload = await request.json()
    object_kind = payload.get("object_kind")
    
    if object_kind == "build":
        return await _handle_build_event(payload)
    
    return {"status": "ignored", "reason": f"Unhandled event type: {object_kind}"}


async def _handle_build_event(payload: dict):
    """Process build (job) events."""
    status = payload.get("build_status")
    
    if status not in ["success", "failed"]:
        return {"status": "ignored", "reason": f"Build status: {status}"}
    
    runner_info = payload.get("runner")
    if not runner_info:
        return {"status": "ignored", "reason": "No runner info"}
    
    runner_name = runner_info.get("description", "unknown")
    duration = payload.get("build_duration", 0)
    
    if runner_name not in RUNNERS:
        logger.warning(f"Unknown runner in webhook: {runner_name}")
        return {"status": "ignored", "reason": f"Unknown runner: {runner_name}"}
    
    success = status == "success"
    cost = RUNNER_COSTS.get(runner_name, 0.0)
    reward = calculate_reward(success, duration, cost)
    
    bandit.update(runner_name, reward, success, duration)
    bandit.save_state(STATE_FILE)
    
    logger.info(f"Webhook update: {runner_name}, {status}, {duration:.1f}s, reward={reward:.4f}")
    
    return {
        "status": "updated",
        "runner": runner_name,
        "build_status": status,
        "reward": round(reward, 4)
    }


@app.get("/stats")
async def get_statistics():
    """Get detailed statistics for all runners."""
    return {
        "algorithm": bandit.__class__.__name__,
        "total_observations": bandit.total_pulls,
        "runners": bandit.get_stats()
    }


@app.post("/reset")
async def reset_bandit():
    """Reset all statistics (use with caution!)."""
    global bandit
    if ALGORITHM == "thompson":
        bandit = ThompsonSamplingBandit(RUNNERS)
    else:
        bandit = UCB1Bandit(RUNNERS, c=2.0)
    
    if STATE_FILE.exists():
        STATE_FILE.unlink()
    
    return {"status": "reset", "algorithm": bandit.__class__.__name__}
