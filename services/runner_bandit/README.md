# Runner Bandit Service 🎰

Intelligent CI Runner Selection using Multi-Armed Bandits.

## Live Deployment

🚀 **URL:** https://runner-bandit-m5cziijwqa-lz.a.run.app

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Service info |
| `/recommend` | GET | Get runner recommendation |
| `/stats` | GET | Detailed statistics |
| `/update` | POST | Manual observation update |
| `/webhooks/gitlab` | POST | GitLab webhook handler |
| `/reset` | POST | Reset all statistics |

## Quick Start

```bash
# Local development
pip install -r requirements.txt
uvicorn src.webhook_handler:app --reload --port 8080

# Docker
docker build -t runner-bandit .
docker run -p 8080:8080 runner-bandit

# Test endpoints
curl http://localhost:8080/
curl http://localhost:8080/recommend
curl http://localhost:8080/stats
```

## Tests

```bash
# Run all tests
pytest tests/ -v

# With coverage
pytest tests/ -v --cov=src --cov-report=term-missing
```

**Test Coverage:**
- `test_bandit.py` - Algorithm unit tests (7 tests)
- `test_api.py` - API integration tests (11 tests)

## CI/CD Pipeline

```
GitLab Registry → skopeo copy → GCP Artifact Registry → Cloud Run
```

**Trigger:** Manual, or changes to `services/runner_bandit/**`

**Pipeline Stages:**
1. `cloud-run:build` - Kaniko → GitLab Registry
2. `cloud-run:copy` - skopeo → GCP Artifact Registry  
3. `cloud-run:deploy` - gcloud → Cloud Run

## GitLab Webhook Integration

The service receives job completion events via GitLab webhook:

```
GitLab Job → Webhook (job_events) → /webhooks/gitlab → MAB Update
```

**Webhook ID:** 69840788 (backoffice project)

## Algorithms

### UCB1 (Upper Confidence Bound) - Default
```
score(a) = Q(a) + c × √(ln(t) / N(a))
```
- Deterministic exploration via confidence bounds
- Theoretical regret: O(√(KT log T))
- Good for: Stable environments, reproducibility

### Thompson Sampling
```
θ(a) ~ Beta(α(a), β(a))
select argmax θ(a)
```
- Probabilistic exploration via posterior sampling
- Often better empirical performance
- Good for: Non-stationary environments

### ε-Greedy
```
P(explore) = ε, P(exploit) = 1-ε
```
- Simple baseline algorithm
- Fixed exploration rate

## Reward Function

```python
reward = success / (duration_minutes + cost_penalty + ε)
```

Where:
- `success` ∈ {0, 1}
- `duration_minutes` = job_duration / 60
- `cost_penalty` = runner_cost × (duration / 3600)
- `ε` = 0.1 (smoothing)

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BANDIT_ALGORITHM` | `ucb1` | Algorithm: `ucb1`, `thompson`, `epsilon_greedy` |
| `BANDIT_STATE_FILE` | `/tmp/bandit_state.json` | State persistence path |
| `GITLAB_WEBHOOK_SECRET` | - | Webhook verification secret |
| `UCB_C` | `2.0` | UCB exploration parameter |
| `EPSILON` | `0.1` | ε-greedy exploration rate |

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  GitLab CI Pipeline                                 │
│  └── Job completes → Webhook                        │
├─────────────────────────────────────────────────────┤
│  MAB Service (Cloud Run)                            │
│  ├── /webhooks/gitlab ← Job events                  │
│  ├── Bandit Algorithm (UCB1/Thompson/ε-greedy)      │
│  ├── /recommend → Runner selection                  │
│  └── /stats → Performance metrics                   │
├─────────────────────────────────────────────────────┤
│  Future: NSAI Integration                           │
│  └── Symbolic CSP → MAB → Optimal Runner            │
└─────────────────────────────────────────────────────┘
```

## Related

- **NSAI Docs:** [services/nsai.md](../../docs/services/nsai.md)
- **Epic:** [#27 - Neurosymbolic AI Runner Selection](/-/issues/27)
- **ADR:** [AI-001](https://gitlab.com/blauweiss_llc/ops/corporate/-/blob/main/docs/adr/ai/AI-001-neurosymbolic-runner-selection.md)
