# Session Summary: CI Runner Migration + MAB Service

**Date:** 2026-02-04  
**Duration:** ~30 min

---

## ✅ Phase 1: CI Minutes Fix (DONE)

| Action | Result |
|--------|--------|
| Root Cause | `gitlab-org-docker` tag (Shared Runner) |
| Fix | Changed to `docker-any` (own runner) |
| Commit | `447855eb` |
| Pipeline | [#2305635899](https://gitlab.com/wolfram_laube/blauweiss_llc/ops/backoffice/-/pipelines/2305635899) |

---

## ✅ MAB Runner Service (DONE)

**Pushed to:** `ops/backoffice/services/runner_bandit/`

**Features:**
- UCB1 Bandit (theoretical guarantees)
- Thompson Sampling (practical performance)
- GitLab Webhook Integration
- State Persistence
- Unit Tests

**Issue:** [#28](https://gitlab.com/wolfram_laube/blauweiss_llc/ops/backoffice/-/issues/28)

---

## 📋 NSAI Epic (PLANNED)

**Epic:** [#27 - Neurosymbolic AI Runner Selection](https://gitlab.com/wolfram_laube/blauweiss_llc/ops/backoffice/-/issues/27)

**Issues Created:**
- #22 Runner Capability Ontology
- #23 Job Requirement Parser  
- #24 Constraint Satisfaction Module
- #25 Neural-Symbolic Interface
- #26 JKU Bachelor Paper Draft

---

## Next Steps

1. **Deploy MAB Service** to GCP Cloud Run
2. **Configure GitLab Webhooks** für Job Events
3. **Collect Data** (2 Wochen Baseline)
4. **Analyze Results** → Paper Material
5. **Implement NSAI** wenn Baseline stabil
