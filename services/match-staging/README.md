# Match Staging Service ("Vorhölle")

Job Match Staging & Multi-Channel Notification Service for the Blauweiss job search automation pipeline.

## Architecture

```
Search → Match (≥70%) → POST /api/v1/matches → GitLab Issue + Notifications
                                                    │
                                   ┌────────────────┼────────────────┐
                                   ▼                ▼                ▼
                                Email           Slack/WA        GitLab ToDo
```

## Quick Start

```bash
# Local development
pip install -e ".[dev]"
uvicorn src.main:app --reload --port 8080

# Docker
docker build -t match-staging .
docker run -p 8080:8080 -e GITLAB_PRIVATE_TOKEN=glpat-... match-staging

# Run tests
pytest -v
```

## API

| Method | Endpoint                     | Description              |
|--------|------------------------------|--------------------------|
| POST   | `/api/v1/matches`            | Stage new match(es)      |
| GET    | `/api/v1/matches`            | List staged matches      |
| PATCH  | `/api/v1/matches/{iid}`      | Approve/Reject           |
| POST   | `/api/v1/notify/test`        | Test all channels        |
| GET    | `/api/v1/config`             | View config              |
| GET    | `/health`                    | Health check             |

## Configuration

Edit `config/notification-channels.yml` or override via environment variables:

```bash
export GITLAB_PRIVATE_TOKEN=glpat-...
export CONFIG__NOTIFICATION__CHANNELS__SLACK__ENABLED=true
export CONFIG__NOTIFICATION__CHANNELS__SLACK__WEBHOOK_URL=https://hooks.slack.com/...
```

## Channels

- **Email**: Gmail API (existing OAuth credentials)
- **Slack**: Incoming Webhook (no bot required)
- **WhatsApp**: Twilio Business API
- **GitLab ToDo**: Native issue assignment

## ADR

See [OPS-004](https://gitlab.com/wolfram.laube/corporate/-/blob/main/docs/adr/operations/OPS-004-job-match-staging-notifications.md) in corporate repo.
