# NSAI - Neurosymbolic AI Runner Selection

> Intelligent CI/CD runner selection combining symbolic reasoning with adaptive learning.

[![Pipeline](https://gitlab.com/blauweiss_llc/ops/backoffice/badges/main/pipeline.svg)](https://gitlab.com/blauweiss_llc/ops/backoffice/-/pipelines)
[![Version](https://img.shields.io/badge/version-0.2.0-blue.svg)](./pyproject.toml)

## Overview

NSAI implements a **two-layer neurosymbolic architecture** for intelligent GitLab CI runner selection:

```
┌─────────────────────────────────────────────────────┐
│  SYMBOLIC LAYER                                     │
│  ├── ontology/   Runner Capability Ontology         │
│  ├── parser/     Job Requirement Parser             │
│  └── csp/        Constraint Satisfaction Solver     │
│                       ↓                             │
│              [Feasible Runner Set]                  │
├─────────────────────────────────────────────────────┤
│  SUBSYMBOLIC LAYER                                  │
│  └── interface/  NeurosymbolicBandit (UCB1)         │
│      ├── Exploration/Exploitation Balance           │
│      └── Learns from Historical Performance         │
│                       ↓                             │
│         [Selected Runner + Explanation]             │
└─────────────────────────────────────────────────────┘
```

## Quick Start

### Simple Usage (Recommended)

```python
from nsai import NeurosymbolicBandit

# Create with production defaults
nsai = NeurosymbolicBandit.create_default()

# Select runner for a job
runner, explanation = nsai.select_runner({
    "tags": ["docker-any"],
    "image": "python:3.11"
})

print(f"Selected: {runner}")
print(explanation)
```

Output:
```
Selected: gitlab-runner-nordic
=== Runner Selection Explanation ===

📐 Symbolic Layer (CSP):
Job requires: docker
Feasible runners: 4
  • gitlab-runner-nordic (score: 1.00, cost: €0.002/min)

🎰 Subsymbolic Layer (MAB):
Evaluating 4 feasible runners:
  → gitlab-runner-nordic: μ=2.467, explore=0.523, UCB=2.990
  ✓ Selected gitlab-runner-nordic (UCB=2.990)

✅ Selected: gitlab-runner-nordic
📊 Confidence: 95.2%
⏱️ Decision time: 1.23ms
```

### With Learning Feedback

```python
# After job completes, update the bandit
nsai.update(
    runner="gitlab-runner-nordic",
    success=True,
    duration_seconds=45.0,
    cost_per_minute=0.002
)

# Future selections will use this experience
runner, _ = nsai.select_runner({"tags": ["docker-any"]})
```

### Sync with MAB Service

```python
import requests

# Fetch stats from deployed MAB service
response = requests.get("https://runner-bandit-m5cziijwqa-lz.a.run.app/stats")
mab_stats = response.json()["runners"]

# Warm-start local NSAI with production data
nsai.sync_from_mab_service(mab_stats)
```

## Modules

### Interface (NEW in v0.2.0)

The `NeurosymbolicBandit` class integrates all layers:

```python
from nsai import NeurosymbolicBandit, NSAI  # NSAI is an alias

nsai = NSAI.create_default()
runner, explanation = nsai.select_runner(job_definition)
```

Key features:
- **Dynamic Action Space**: Only considers feasible runners → faster convergence
- **UCB1 Algorithm**: Balances exploration vs exploitation  
- **Transparent Explanations**: Human-readable reasoning
- **MAB Sync**: Warm-start from deployed service

### Ontology

Semantic model for runner capabilities:

```python
from nsai import RunnerOntology, create_blauweiss_ontology

# Use production ontology
onto = create_blauweiss_ontology()

# Or create custom
onto = RunnerOntology()
onto.add_runner("my-runner", capabilities=["docker", "linux", "gpu"])
```

### Parser

Extracts requirements from `.gitlab-ci.yml`:

```python
from nsai import JobRequirementParser

parser = JobRequirementParser()
reqs = parser.parse({
    "tags": ["docker-any"],
    "image": "nvidia/cuda:11.8"
})
# reqs.required_capabilities = ["docker"]
# reqs.preferred_capabilities = ["gpu"]
```

### CSP Solver

Direct constraint satisfaction (used internally by NeurosymbolicBandit):

```python
from nsai import ConstraintSolver, create_blauweiss_ontology

solver = ConstraintSolver(
    ontology=create_blauweiss_ontology(),
    parser=JobRequirementParser()
)
result = solver.solve({"tags": ["docker-any"]})
print(result.feasible_runners)
```

## Installation

```bash
# From backoffice root
pip install -e services/nsai/

# Or just the dependencies
pip install -r services/nsai/requirements.txt
```

## Testing

```bash
# All NSAI tests
pytest services/nsai/tests/ -v

# With coverage
pytest services/nsai/tests/ -v --cov=nsai --cov-report=term-missing

# Just interface tests
pytest services/nsai/tests/test_interface.py -v
```


## Testing

### Unit Tests

```bash
# All NSAI tests
pytest services/nsai/tests/ -v

# With coverage (minimum 80% required)
pytest services/nsai/tests/ -v --cov=nsai --cov-report=term-missing
```

### Notebook Smoke Tests

**⚠️ IMPERATIVE:** All notebooks MUST include smoke tests.

```bash
# Run notebook smoke tests
cd services/nsai/notebooks
jupyter nbconvert --execute demo.ipynb --to notebook
```

The `demo.ipynb` includes 8 smoke tests that verify all components work correctly.
Run the "Smoke Tests" section first when exploring the notebook.

See [CONTRIBUTING.md](./CONTRIBUTING.md) for full testing requirements.

## API Reference

### NeurosymbolicBandit

| Method | Description |
|--------|-------------|
| `create_default()` | Factory with production ontology |
| `select_runner(job_def, job_name)` | Returns `(runner, explanation)` |
| `update(runner, success, duration, cost)` | Update stats after job |
| `get_stats()` | Current runner statistics |
| `sync_from_mab_service(stats)` | Warm-start from MAB service |

### Explanation

| Field | Type | Description |
|-------|------|-------------|
| `symbolic_reasoning` | str | Why runners were filtered |
| `statistical_reasoning` | str | Why runner was selected |
| `feasible_runners` | List[str] | Runners passing CSP |
| `selected_runner` | str | Final selection |
| `confidence` | float | Selection confidence (0-1) |
| `solve_time_ms` | float | Decision time |

## Architecture Decision Records

| ID | Title | Status |
|----|-------|--------|
| [AI-001](../../../corporate/docs/adr/ai/AI-001-neurosymbolic-runner-selection.md) | Neurosymbolic Runner Selection | ✅ Accepted |

## Related

- **Epic:** [#27 Neurosymbolic AI Runner Selection](../../issues/27)
- **MAB Service:** [runner_bandit/](../runner_bandit/) | [Cloud Run](https://runner-bandit-m5cziijwqa-lz.a.run.app)
- **Paper:** [#26 JKU Bachelor Paper Draft](../../issues/26)
- **Demo:** [notebooks/demo.ipynb](./notebooks/demo.ipynb)

## License

Internal use only - Blauweiss LLC

## ⚠️ Testing Requirements

### IMPERATIVE: Notebooks MUST be tested!

All notebooks in `notebooks/` contain executable code that serves as documentation.
**Broken notebooks mislead users and MUST NOT be merged.**

```bash
# Validate all notebooks execute without errors
pytest --nbval notebooks/ -v

# With timeout for long-running cells
pytest --nbval --nbval-cell-timeout=120 notebooks/ -v
```

### CI Enforcement

The `test:nsai:notebooks` job runs automatically on:
- Every MR that touches `services/nsai/`
- Every push to `main` that changes notebooks

See [CONTRIBUTING.md](./CONTRIBUTING.md) for full testing guidelines.

### Adding Assertions to Notebooks

Every notebook should include assertions to verify expected behavior:

```python
# Good: Verifiable assertions
result = solver.solve(job)
assert result.is_feasible, "Expected feasible result"
assert len(result.feasible_runners) > 0

# Bad: No verification
result = solver.solve(job)
print(result)  # How do we know this is correct?
```
