"""Job Match Staging & Notification Service.

FastAPI application providing REST API for:
- Staging matched job leads as GitLab Issues
- Multi-channel notifications (Email, Slack, WhatsApp, GitLab ToDo)
- Review workflow (pending → approved/rejected → sent)
- Configuration management
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.config import ServiceConfig, get_config, reload_config
from src.adapters.gitlab_adapter import GitLabAdapter
from src.dispatcher import NotificationDispatcher
from src.models import (
    JobMatch,
    MatchState,
    NotificationPayload,
    StagedMatch,
    StagingRequest,
    StagingResponse,
    StateTransition,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Global state ---
dispatcher: NotificationDispatcher | None = None
gitlab: GitLabAdapter | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup."""
    global dispatcher, gitlab
    config = get_config()
    dispatcher = NotificationDispatcher(config)
    gitlab = GitLabAdapter(config.gitlab, config.notification.channels.gitlab_todo)
    logger.info(
        f"Service started. Channels: {dispatcher.enabled_channels}"
    )
    yield
    logger.info("Service shutdown.")


app = FastAPI(
    title="Match Staging Service",
    description="Job Match Staging & Multi-Channel Notification (Vorhölle)",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Health ---


@app.get("/health")
async def health():
    """Service health check including channel status."""
    channel_health = await dispatcher.health_check() if dispatcher else {}
    return {
        "status": "ok",
        "channels": channel_health,
        "enabled": dispatcher.enabled_channels if dispatcher else [],
    }


# --- Match Staging ---


@app.post("/api/v1/matches", response_model=StagingResponse)
async def stage_matches(request: StagingRequest):
    """Stage one or more job matches.

    Creates GitLab Issues and sends notifications via configured channels.
    """
    if not gitlab:
        raise HTTPException(503, "Service not initialized")

    config = get_config()
    threshold = config.notification.preferences.threshold
    staged: list[StagedMatch] = []
    errors: list[str] = []

    # Filter by threshold
    qualified = [m for m in request.matches if m.overall_score >= threshold]
    if not qualified:
        return StagingResponse(
            cycle_id=request.cycle_id,
            staged=[],
            errors=[
                f"No matches above threshold ({threshold}%). "
                f"Received scores: {[m.overall_score for m in request.matches]}"
            ],
        )

    # Stage each match as GitLab Issue
    attachments = []
    if request.attach_profile:
        attachments.append(config.profile_path)
    if request.attach_cv:
        attachments.append(config.cv_path)

    for match in qualified:
        try:
            staged_match = await gitlab.create_issue(
                match=match,
                cycle_id=request.cycle_id,
                attachments=attachments,
            )
            staged.append(staged_match)
            logger.info(
                f"Staged: {match.overall_score}% {match.title} "
                f"→ #{staged_match.gitlab_issue_iid}"
            )
        except Exception as e:
            error_msg = f"Failed to stage '{match.title}': {e}"
            logger.error(error_msg)
            errors.append(error_msg)

    # Notify via all channels
    notifications_sent: list[str] = []
    if staged and request.auto_notify and dispatcher:
        review_url = (
            f"https://gitlab.com/wolfram.laube/backoffice/-/issues"
            f"?label_name[]=job-match%2Fpending"
        )
        payload = NotificationPayload.from_staged(
            cycle_id=request.cycle_id,
            staged=staged,
            review_url=review_url,
        )
        results = await dispatcher.dispatch(payload)
        notifications_sent = [ch for ch, ok in results.items() if ok]

    return StagingResponse(
        cycle_id=request.cycle_id,
        staged=staged,
        notifications_sent=notifications_sent,
        errors=errors,
    )


@app.get("/api/v1/matches")
async def list_matches(state: MatchState | None = None):
    """List staged matches, optionally filtered by state."""
    if not gitlab:
        raise HTTPException(503, "Service not initialized")

    config = get_config()
    labels = "job-match"
    if state:
        labels += f",job-match/{state.value}"

    import httpx

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{gitlab.base}/issues",
            headers=gitlab.headers,
            params={"labels": labels, "per_page": 50, "state": "all"},
        )
        resp.raise_for_status()
        return resp.json()


@app.patch("/api/v1/matches/{issue_iid}")
async def transition_match(issue_iid: int, transition: StateTransition):
    """Transition a match to a new state (approve/reject/sent)."""
    if not gitlab:
        raise HTTPException(503, "Service not initialized")

    try:
        success = await gitlab.transition_state(
            issue_iid=issue_iid,
            new_state=transition.new_state,
            comment=transition.comment,
        )
        return {"success": success, "new_state": transition.new_state}
    except Exception as e:
        raise HTTPException(500, f"Transition failed: {e}")


# --- Notification ---


@app.post("/api/v1/notify/test")
async def test_notification():
    """Send a test notification to all enabled channels."""
    if not dispatcher:
        raise HTTPException(503, "Dispatcher not initialized")

    test_match = JobMatch(
        title="Test Match — Cloud Architect",
        provider="Test Provider GmbH",
        location="Wien (100% Remote)",
        remote_percentage=100,
        start_date="ASAP",
        duration="6 Mo",
        rate_eur=105,
        overall_score=95,
        strengths=["This is a test notification"],
    )
    payload = NotificationPayload.from_staged(
        cycle_id="test-cycle",
        staged=[
            StagedMatch(
                match=test_match,
                gitlab_issue_id=0,
                gitlab_issue_iid=0,
                gitlab_issue_url="https://gitlab.com/test",
            )
        ],
        review_url="https://gitlab.com/wolfram.laube/backoffice/-/issues?label_name[]=job-match",
    )

    results = await dispatcher.dispatch(payload, force=True)
    return {"results": results}


# --- Config ---


@app.get("/api/v1/config")
async def get_notification_config():
    """Get current notification configuration."""
    config = get_config()
    # Redact secrets
    cfg = config.notification.model_dump()
    if cfg["channels"]["whatsapp"].get("auth_token"):
        cfg["channels"]["whatsapp"]["auth_token"] = "***"
    if cfg["channels"]["slack"].get("webhook_url"):
        url = cfg["channels"]["slack"]["webhook_url"]
        cfg["channels"]["slack"]["webhook_url"] = url[:30] + "***" if url else ""
    return cfg


@app.put("/api/v1/config")
async def update_config(config_update: dict):
    """Update notification configuration (runtime only, not persisted to YAML)."""
    # In production, this would merge and write back to YAML
    # For now, just reload from file
    config = reload_config()
    return {"status": "reloaded", "channels": config.notification.channels.model_dump()}
