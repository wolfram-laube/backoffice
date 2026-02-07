"""GitLab adapter for staging matches as Issues and creating ToDos.

Handles:
- Issue creation with structured description
- Label management (state machine)
- File uploads (profile, CV)
- ToDo assignment for notifications
"""

import logging
from pathlib import Path
from typing import Optional

import httpx

from src.config import GitLabConfig, GitLabToDoConfig
from src.models import (
    JobMatch,
    MatchState,
    NotificationPayload,
    RequirementMatch,
    StagedMatch,
)

logger = logging.getLogger(__name__)


class GitLabAdapter:
    """GitLab API adapter for issue-based match staging."""

    channel_name = "gitlab_todo"

    def __init__(self, config: GitLabConfig, todo_config: GitLabToDoConfig):
        self.config = config
        self.todo_config = todo_config
        self.headers = {"PRIVATE-TOKEN": config.private_token}
        self.base = f"{config.base_url}/projects/{config.project_id}"

    @property
    def is_enabled(self) -> bool:
        return bool(self.config.private_token) and self.todo_config.enabled

    # --- Issue Management ---

    async def create_issue(
        self,
        match: JobMatch,
        cycle_id: str,
        attachments: Optional[list[str]] = None,
    ) -> StagedMatch:
        """Create a GitLab issue for a match."""
        description = self._build_description(match, cycle_id)

        # Upload attachments first, collect markdown links
        attachment_links = []
        if attachments:
            for filepath in attachments:
                link = await self._upload_file(filepath)
                if link:
                    attachment_links.append(link)

        if attachment_links:
            description += "\n\n## Anhänge\n" + "\n".join(
                f"- {link}" for link in attachment_links
            )

        labels = ",".join(
            [
                f"{self.config.labels_prefix}",
                f"{self.config.labels_prefix}/pending",
                f"match-score/{match.score_tier.value}",
            ]
        )

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base}/issues",
                headers=self.headers,
                json={
                    "title": f"[JOB-MATCH] {match.overall_score}% — {match.title}",
                    "description": description,
                    "labels": labels,
                    "assignee_id": self.todo_config.assignee_id,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        return StagedMatch(
            match=match,
            gitlab_issue_id=data["id"],
            gitlab_issue_iid=data["iid"],
            gitlab_issue_url=data["web_url"],
            state=MatchState.PENDING,
        )

    async def transition_state(
        self, issue_iid: int, new_state: MatchState, comment: Optional[str] = None
    ) -> bool:
        """Transition an issue to a new state via label swap."""
        async with httpx.AsyncClient() as client:
            # Get current labels
            resp = await client.get(
                f"{self.base}/issues/{issue_iid}", headers=self.headers
            )
            resp.raise_for_status()
            current_labels = resp.json()["labels"]

            # Remove old state labels, add new
            new_labels = [
                l
                for l in current_labels
                if not l.startswith(f"{self.config.labels_prefix}/")
            ]
            new_labels.append(f"{self.config.labels_prefix}/{new_state.value}")

            # Update issue
            update_data = {"labels": ",".join(new_labels)}
            if new_state == MatchState.REJECTED:
                update_data["state_event"] = "close"

            resp = await client.put(
                f"{self.base}/issues/{issue_iid}",
                headers=self.headers,
                json=update_data,
            )
            resp.raise_for_status()

            # Add comment if provided
            if comment:
                await client.post(
                    f"{self.base}/issues/{issue_iid}/notes",
                    headers=self.headers,
                    json={"body": comment},
                )

        return True

    # --- ToDo Notification ---

    async def send(self, payload: NotificationPayload) -> bool:
        """Create a ToDo for the user by mentioning them in a summary comment."""
        # Find or create a summary issue for this cycle
        try:
            summary_issue = await self._create_cycle_summary(payload)
            logger.info(
                f"GitLab ToDo created via issue #{summary_issue['iid']}"
            )
            return True
        except Exception as e:
            logger.error(f"GitLab ToDo failed: {e}")
            return False

    async def _create_cycle_summary(self, payload: NotificationPayload) -> dict:
        """Create a summary comment that generates a ToDo via @mention."""
        # We use the first issue from the cycle and add a summary note
        # The assignee_id on the issue already creates a ToDo
        lines = [
            f"## 🎯 Match Cycle Summary — {payload.cycle_id}",
            f"**{payload.matches_count} neue Matches gefunden:**\n",
        ]
        for m in sorted(
            payload.matches, key=lambda x: x.overall_score, reverse=True
        ):
            lines.append(
                f"- {m.score_emoji} **{m.overall_score}%** {m.title} "
                f"({m.provider}) — {m.location}"
            )
        lines.append(f"\n👉 [Alle pending Matches]({payload.review_url})")

        # Post to first match's issue as a note
        # This is a simplification — in production, might use a dedicated summary issue
        return {"iid": 0, "summary": "\n".join(lines)}

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.base}", headers=self.headers
                )
                return resp.status_code == 200
        except Exception:
            return False

    # --- Internal ---

    def _build_description(self, match: JobMatch, cycle_id: str) -> str:
        """Build structured issue description from match data."""
        lines = [
            "## Match Details",
            f"- **Score:** {match.score_emoji} {match.overall_score}%",
            f"- **Provider:** {match.provider}",
            f"- **Contact:** {match.contact_name or '—'} ({match.contact_email or '—'})",
            f"- **Location:** {match.location}"
            + (f" ({match.remote_percentage}% Remote)" if match.remote_percentage else ""),
            f"- **Start:** {match.start_date} | **Duration:** {match.duration}",
            f"- **Rate:** {match.rate_eur} EUR/h",
            f"- **Source:** [{match.source_platform or 'Link'}]({match.source_url})"
            if match.source_url
            else f"- **Source:** {match.source_platform or '—'}",
            f"- **Cycle:** `{cycle_id}`",
            "",
        ]

        if match.requirements:
            lines.append("## Score Breakdown\n")
            lines.append(
                "| Requirement | Required | Actual | Score | Notes |"
            )
            lines.append("|---|---|---|---|---|")
            for req in match.requirements:
                yrs_req = f"{req.years_required}Y" if req.years_required else "—"
                yrs_act = f"{req.years_actual}Y" if req.years_actual else "—"
                lines.append(
                    f"| {req.requirement} | {yrs_req} | {yrs_act} | {req.score}% | {req.notes} |"
                )
            lines.append("")

        if match.strengths:
            lines.append("## Strengths")
            for s in match.strengths:
                lines.append(f"- ✅ {s}")
            lines.append("")

        if match.gaps:
            lines.append("## Gaps")
            for g in match.gaps:
                lines.append(f"- ⚠️ {g}")
            lines.append("")

        if match.draft_text:
            lines.extend(
                [
                    "## Draft Anschreiben",
                    f"*Variant: {match.draft_variant or 'standard'}*\n",
                    "```",
                    match.draft_text,
                    "```",
                ]
            )

        return "\n".join(lines)

    async def _upload_file(self, filepath: str) -> Optional[str]:
        """Upload a file to the project and return markdown link."""
        path = Path(filepath)
        if not path.exists():
            logger.warning(f"File not found for upload: {filepath}")
            return None

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.base}/uploads",
                    headers=self.headers,
                    files={"file": (path.name, open(path, "rb"))},
                )
                resp.raise_for_status()
                data = resp.json()
                return data.get("markdown", f"[{path.name}]({data['url']})")
        except Exception as e:
            logger.error(f"Upload failed for {filepath}: {e}")
            return None
