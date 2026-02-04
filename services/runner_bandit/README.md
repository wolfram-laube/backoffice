# Runner Bandit Service 🎰

Intelligent CI Runner Selection using Multi-Armed Bandits.

## Quick Start

```bash
# Local development
pip install -r requirements.txt
uvicorn src.webhook_handler:app --reload --port 8080

# Docker
docker build -t runner-bandit .
docker run -p 8080:8080 -v $(pwd)/data:/data runner-bandit
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Service info |
| `/recommend` | GET | Get runner recommendation |
| `/update` | POST | Manual observation update |
| `/webhooks/gitlab` | POST | GitLab webhook handler |
| `/stats` | GET | Detailed statistics |
| `/reset` | POST | Reset all statistics |

## Environment Variables

- `BANDIT_ALGORITHM`: `ucb1` (default) or `thompson`
- `BANDIT_STATE_FILE`: Path to persist state (default: `/tmp/bandit_state.json`)
- `GITLAB_WEBHOOK_SECRET`: Secret for webhook verification

## Algorithms

### UCB1 (Upper Confidence Bound)
- Deterministic exploration via confidence bounds
- Theoretical regret guarantees: O(√(KT log T))
- Good for: Stable environments, reproducibility

### Thompson Sampling
- Probabilistic exploration via posterior sampling
- Often better empirical performance
- Good for: Non-stationary environments, quick adaptation

## Reward Function

```
reward = success / (duration_minutes + cost_penalty + ε)
```

Where:
- `success` ∈ {0, 1}
- `duration_minutes` = job runtime / 60
- `cost_penalty` = runner_cost_per_hour × (duration / 3600)
- `ε` = 0.1 (smoothing factor)
