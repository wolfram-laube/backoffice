# 🧠 NSAI - Neurosymbolic AI Runner Selection

> Intelligent CI/CD runner selection combining symbolic reasoning with adaptive learning.

**Status:** ✅ Baseline Deployed  
**Service URL:** https://runner-bandit-m5cziijwqa-lz.a.run.app  
**ADR:** [AI-001](https://gitlab.com/blauweiss_llc/ops/corporate/-/blob/main/docs/adr/ai/AI-001-neurosymbolic-runner-selection.md)  
**Epic:** [#27](https://gitlab.com/blauweiss_llc/ops/backoffice/-/issues/27)

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  SYMBOLIC LAYER (Implemented ✅)                    │
│  ├── ontology/   Runner Capability Ontology         │
│  ├── parser/     Job Requirement Parser             │
│  └── csp/        Constraint Satisfaction Solver     │
│                       ↓                             │
│              [Feasible Runner Set]                  │
├─────────────────────────────────────────────────────┤
│  SUBSYMBOLIC LAYER (Deployed ✅)                    │
│  └── runner_bandit/  Multi-Armed Bandit Selection   │
│      (UCB1, Thompson Sampling, ε-Greedy)            │
│      🚀 Cloud Run: europe-north1                    │
│                       ↓                             │
│              [Selected Runner]                      │
└─────────────────────────────────────────────────────┘
```

---

## MAB Runner Bandit Service

**Live:** https://runner-bandit-m5cziijwqa-lz.a.run.app

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/recommend` | GET | Get runner recommendation |
| `/stats` | GET | Current statistics |
| `/update` | POST | Update with job result |
| `/webhooks/gitlab` | POST | GitLab webhook receiver |

**Algorithms:**
- UCB1 (Upper Confidence Bound) - default
- Thompson Sampling
- ε-Greedy

---

## Modules

### Ontology (`services/nsai/ontology/`)

Semantic model for runner capabilities using OWL-inspired classes.

```python
from nsai.ontology import RunnerOntology, create_blauweiss_ontology

onto = create_blauweiss_ontology()
runners = onto.get_runners_with_capability("docker")
```

### Parser (`services/nsai/parser/`)

Extracts requirements from `.gitlab-ci.yml` job definitions.

```python
from nsai.parser import JobRequirementParser

parser = JobRequirementParser()
reqs = parser.parse({"tags": ["docker-any"], "image": "nvidia/cuda:11.8"})
```

### CSP Solver (`services/nsai/csp/`)

Finds feasible runners by matching requirements against capabilities.

```python
from nsai.csp import ConstraintSolver

solver = ConstraintSolver(ontology, parser)
result = solver.solve(job_definition)
```

---

## Issues & Progress

| Issue | Title | Status |
|-------|-------|--------|
| [#22](/-/issues/22) | Runner Capability Ontology | ✅ Done |
| [#23](/-/issues/23) | Job Requirement Parser | ✅ Done |
| [#24](/-/issues/24) | Constraint Satisfaction Module | ✅ Done |
| [#28](/-/issues/28) | MAB Baseline Service | ✅ Done |
| [#25](/-/issues/25) | Neural-Symbolic Interface | 📋 Planned |
| [#26](/-/issues/26) | JKU Bachelor Paper Draft | 📋 Planned |

---

## Tests

```bash
# MAB tests
pytest services/runner_bandit/tests/ -v

# NSAI tests
pytest services/nsai/tests/ -v
```

---

## Related

- **MAB Service:** [`services/runner_bandit/`](/-/tree/main/services/runner_bandit)
- **CI/CD:** GitLab Registry → GCP Artifact Registry → Cloud Run
- **JKU Paper:** Q1 2026
