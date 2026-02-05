# 🧠 NSAI - Neurosymbolic AI Runner Selection

> Intelligent CI/CD runner selection combining symbolic reasoning with adaptive learning.

**Status:** ✅ Symbolic Layer Implemented  
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
│  SUBSYMBOLIC LAYER (In Progress 🔄)                 │
│  └── runner_bandit/  Multi-Armed Bandit Selection   │
│      (UCB1, Thompson Sampling, ε-Greedy)            │
│                       ↓                             │
│              [Selected Runner]                      │
└─────────────────────────────────────────────────────┘
```

---

## Modules

### Ontology (`services/nsai/ontology/`)

Semantic model for runner capabilities using OWL-inspired classes.

```python
from nsai.ontology import RunnerOntology, create_blauweiss_ontology

onto = create_blauweiss_ontology()
runners = onto.get_runners_with_capability("docker")
```

**Features:**

- Standard capability taxonomy (executor, platform, cloud, hardware)
- Capability implications (e.g., `nordic` → `gcp`, `eu-west`)
- Runner registration with cost tracking

### Parser (`services/nsai/parser/`)

Extracts requirements from `.gitlab-ci.yml` job definitions.

```python
from nsai.parser import JobRequirementParser

parser = JobRequirementParser()
reqs = parser.parse({"tags": ["docker-any"], "image": "nvidia/cuda:11.8"})
# reqs.required_capabilities = ["docker"]
# reqs.preferred_capabilities = ["gpu"]
```

**Features:**

- Tag-to-capability mapping
- Image/service inference
- Timeout parsing
- Full YAML parsing support

### CSP Solver (`services/nsai/csp/`)

Finds feasible runners by matching requirements against capabilities.

```python
from nsai.csp import ConstraintSolver

solver = ConstraintSolver(ontology, parser)
result = solver.solve(job_definition)

print(result.feasible_runners)  # ["gitlab-runner-nordic"]
print(result.explanation)       # Human-readable reasoning
```

**Features:**

- Feasibility checking with pruning
- Preference scoring for ranking
- Batch solving for multiple jobs
- Explanation generation

---

## Issues & Progress

| Issue | Title | Status |
|-------|-------|--------|
| [#22](https://gitlab.com/blauweiss_llc/ops/backoffice/-/issues/22) | Runner Capability Ontology | ✅ Done |
| [#23](https://gitlab.com/blauweiss_llc/ops/backoffice/-/issues/23) | Job Requirement Parser | ✅ Done |
| [#24](https://gitlab.com/blauweiss_llc/ops/backoffice/-/issues/24) | Constraint Satisfaction Module | ✅ Done |
| [#25](https://gitlab.com/blauweiss_llc/ops/backoffice/-/issues/25) | Neural-Symbolic Interface | 📋 Planned |
| [#26](https://gitlab.com/blauweiss_llc/ops/backoffice/-/issues/26) | JKU Bachelor Paper Draft | 📋 Planned |
| [#28](https://gitlab.com/blauweiss_llc/ops/backoffice/-/issues/28) | MAB Baseline Service | 🔄 In Progress |

---

## Tests

```bash
# Run all NSAI tests
pytest services/nsai/tests/ -v

# With coverage
pytest services/nsai/tests/ -v --cov=nsai
```

**Current:** 46/46 tests passing ✅

---

## Related

- **MAB Service:** [`services/runner_bandit/`](https://gitlab.com/blauweiss_llc/ops/backoffice/-/tree/main/services/runner_bandit)
- **ADR:** [AI-001 Neurosymbolic Runner Selection](https://gitlab.com/blauweiss_llc/ops/corporate/-/blob/main/docs/adr/ai/AI-001-neurosymbolic-runner-selection.md)
- **JKU Paper:** Coming Q1 2026
