# NSAI - Neurosymbolic AI Runner Selection

> Intelligent CI/CD runner selection combining symbolic reasoning with adaptive learning.

[![Pipeline](https://gitlab.com/blauweiss_llc/ops/backoffice/badges/main/pipeline.svg)](https://gitlab.com/blauweiss_llc/ops/backoffice/-/pipelines)
[![Coverage](https://gitlab.com/blauweiss_llc/ops/backoffice/badges/main/coverage.svg)](https://gitlab.com/blauweiss_llc/ops/backoffice/-/commits/main)

## Overview

NSAI implements a two-layer architecture for intelligent GitLab CI runner selection:

```
┌─────────────────────────────────────────────────────┐
│  SYMBOLIC LAYER (This Module)                       │
│  ├── ontology/   Runner Capability Ontology (OWL)   │
│  ├── parser/     Job Requirement Parser             │
│  └── csp/        Constraint Satisfaction Solver     │
│                       ↓                             │
│              [Feasible Runner Set]                  │
├─────────────────────────────────────────────────────┤
│  SUBSYMBOLIC LAYER (runner_bandit service)          │
│  └── Multi-Armed Bandit Selection                   │
│      (UCB1, Thompson Sampling, ε-Greedy)            │
│                       ↓                             │
│              [Selected Runner]                      │
└─────────────────────────────────────────────────────┘
```

## Quick Start

```python
from nsai.ontology import create_blauweiss_ontology
from nsai.parser import JobRequirementParser
from nsai.csp import ConstraintSolver

# Create solver with production ontology
solver = ConstraintSolver(
    ontology=create_blauweiss_ontology(),
    parser=JobRequirementParser()
)

# Solve for a job
result = solver.solve(
    job_definition={"tags": ["docker-any"], "image": "python:3.11"},
    job_name="my-test-job"
)

print(f"Feasible: {result.is_feasible}")
print(f"Best runner: {result.best_runner}")
print(f"Explanation:\n{result.explanation}")
```

## Modules

### Ontology (#22)

Semantic model for runner capabilities using OWL-inspired classes.

```python
from nsai.ontology import RunnerOntology

onto = RunnerOntology()
onto.add_runner("my-runner", capabilities=["docker", "linux", "gpu"])
runners = onto.get_runners_with_capability("gpu")
```

### Parser (#23)

Extracts requirements from `.gitlab-ci.yml` job definitions.

```python
from nsai.parser import JobRequirementParser

parser = JobRequirementParser()
reqs = parser.parse({"tags": ["docker-any"], "image": "nvidia/cuda:11.8"})
# reqs.required_capabilities = ["docker"]
# reqs.preferred_capabilities = ["gpu"]
```

### CSP Solver (#24)

Finds feasible runners by matching requirements against capabilities.

```python
from nsai.csp import ConstraintSolver

solver = ConstraintSolver(ontology, parser)
result = solver.solve(job_definition)
# result.feasible_runners, result.ranked_runners, result.explanation
```

## Installation

```bash
pip install -e services/nsai/
```

## Testing

```bash
# Run all NSAI tests
pytest services/nsai/tests/ -v

# With coverage
pytest services/nsai/tests/ -v --cov=nsai --cov-report=term-missing
```

## Related

- **ADR:** [AI-001 Neurosymbolic Runner Selection](../../../corporate/docs/adr/ai/AI-001-neurosymbolic-runner-selection.md)
- **Epic:** [#27 Neurosymbolic AI Runner Selection](../../issues/27)
- **MAB Service:** [runner_bandit/](../runner_bandit/)
- **Paper:** [#26 JKU Bachelor Paper Draft](../../issues/26)

## Architecture Decision Records

| ID | Title | Status |
|----|-------|--------|
| AI-001 | Neurosymbolic Runner Selection | 🔄 Proposed |

## License

Internal use only - Blauweiss LLC
