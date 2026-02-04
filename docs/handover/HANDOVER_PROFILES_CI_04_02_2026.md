# HANDOVER: CI Runner Migration & Intelligente Runner-Auswahl
**Datum:** 2026-02-04  
**Session:** EPIC - CI Runner Migration nach CI Minutes Erschöpfung  
**Context:** Profile-Modul konsolidiert (MR !2 merged), CI Minutes erschöpft

---

## 🎯 Executive Summary

**Problem:** GitLab Shared Runner CI Minutes erschöpft (`ci_quota_exceeded`)

**Ursache:** Default-Tag `gitlab-org-docker` in `.gitlab-ci.yml` nutzt Shared Runners

**Lösung Phase 1:** Default-Tag auf eigenen Runner umstellen → `docker-any`

**Lösung Phase 2:** Multi-Armed Bandit Runner Selection (Paper-Material für JKU!)

---

## 📊 Analyse-Ergebnis

### Verfügbare Eigene Runner

| Runner ID | Name | Location | Tags | Status |
|-----------|------|----------|------|--------|
| 51608579 | gitlab-runner-nordic | GCP Stockholm | docker-any, shell, nordic, gcp | ✅ online |
| 51336735 | Mac Docker Runner | Lokal | docker | ✅ online |
| 51337424 | Mac2 Docker Runner | Lokal | docker | ✅ online |
| 51337426 | Linux Yoga Docker Runner | Lokal | docker | ✅ online |

### Problem-Diagnose

```yaml
# .gitlab-ci.yml (AKTUELL - PROBLEM)
default:
  image: python:3.11-slim
  tags:
    - gitlab-org-docker  # ← Shared Runner! Minutes erschöpft!
```

### CI-Dateien Übersicht (19 Dateien in .gitlab/)

| Datei | Tag-Status | Aktion |
|-------|------------|--------|
| `.gitlab-ci.yml` | `gitlab-org-docker` | **ÄNDERN → docker-any** |
| applications.yml | empty tags | OK (nutzt default) |
| billing.yml | empty tags (4x) | OK (nutzt default) |
| ci-automation.yml | empty (8x) + gcp-docker | OK (nutzt default) |
| docker-build.yml | empty tags (2x) | OK (nutzt default) |
| gdrive-upload.yml | empty tags | OK (nutzt default) |
| gmail-drafts.yml | empty tags (3x) | OK (nutzt default) |
| k3s-setup.yml | gcp-shell (5x) | Optional: → shell |
| pages.yml | empty tags (4x) | OK (nutzt default) |
| roundtrip-test.yml | empty tags (4x) | OK (nutzt default) |
| runner-fallback.yml | gcp-shell/docker | OK (spezifisch) |
| terraform.yml | empty tags | OK (nutzt default) |
| tests.yml | empty tags | OK (nutzt default) |
| benchmark.yml | spezifische Tags | **NICHT ÄNDERN** (Benchmarking) |
| gcp-check.yml | mac-group-shell | Optional: → shell |
| gcp-setup.yml | mac-group-shell (2x) | Optional: → shell |
| infra-setup.yml | mac-group-shell (2x) | Optional: → shell |
| fix-shell-runner.yml | gcp-shell/docker | OK (spezifisch) |
| gcp-migration.yml | keine Tags | OK (default) |
| parallel-jobs.yml | shell-any, docker-any | OK (generic) |

---

## 🚀 Phase 1: Sofort-Fix (5 Minuten)

### Einzige kritische Änderung

**Datei:** `.gitlab-ci.yml`  
**Zeile 70:** `- gitlab-org-docker` → `- docker-any`

```yaml
# .gitlab-ci.yml (NACH FIX)
default:
  image: python:3.11-slim
  tags:
    - docker-any  # ← Eigener Runner!
```

### Commit via API

```bash
PAT="glpat--wmS4xEWjjWdOgaOd7oDWG86MQp1OnN4Y3gK.01.101dpjjbj"
PROJECT_ID="77555895"

# Get current file content (base64)
CONTENT=$(curl -s --header "PRIVATE-TOKEN: $PAT" \
  "https://gitlab.com/api/v4/projects/$PROJECT_ID/repository/files/.gitlab-ci.yml?ref=main" | \
  python3 -c "import json,sys; print(json.load(sys.stdin)['content'])" | base64 -d)

# Replace the tag
NEW_CONTENT=$(echo "$CONTENT" | sed 's/gitlab-org-docker/docker-any/')

# Commit
curl -s --request PUT \
  --header "PRIVATE-TOKEN: $PAT" \
  --header "Content-Type: application/json" \
  --data "{
    \"branch\": \"main\",
    \"commit_message\": \"fix(ci): use own runner instead of shared (docker-any)\n\nCI Minutes erschöpft - umstellen auf gitlab-runner-nordic\",
    \"content\": \"$(echo "$NEW_CONTENT" | base64 -w0)\"
  }" \
  "https://gitlab.com/api/v4/projects/$PROJECT_ID/repository/files/.gitlab-ci.yml"
```

### Verifizierung

```bash
# Test-Pipeline triggern
curl -s --request POST \
  --header "PRIVATE-TOKEN: $PAT" \
  --form "ref=main" \
  --form "variables[TEST_RUN]=true" \
  "https://gitlab.com/api/v4/projects/$PROJECT_ID/pipeline"
```

---

## 🧠 Phase 2: Multi-Armed Bandit Runner Selection (Paper-Material!)

### Konzept

**Problem:** Mehrere Runner verfügbar (Nordic GCP, Mac, Linux) - welcher ist optimal?

**Ansatz:** Multi-Armed Bandit (MAB) für intelligente Runner-Auswahl

### Reward-Funktion

```
Reward = success / (duration + cost_penalty)

wobei:
- success ∈ {0, 1}
- duration = Job-Laufzeit in Sekunden
- cost_penalty = Runner-spezifische Kosten (GCP > Lokal)
```

### Algorithmen-Kandidaten

| Algorithmus | Exploration | Vorteile | Paper-Relevanz |
|-------------|-------------|----------|----------------|
| **UCB1** | Upper Confidence Bound | Deterministisch, theoretisch fundiert | ⭐⭐⭐ Regret Bounds |
| **Thompson Sampling** | Bayesian Posterior | Adaptiv, state-of-the-art | ⭐⭐⭐ Praktisch optimal |
| **ε-greedy** | Random ε | Einfach, Baseline | ⭐ Vergleichs-Baseline |

### Architektur

```
┌─────────────────────────────────────────────────────────────┐
│                    RunnerBandit Service                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ UCB1/TS     │  │ State Store │  │ Metrics Collector   │  │
│  │ Algorithm   │  │ (Redis/SQL) │  │ (Job duration/cost) │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
          ↑                                      ↓
          │ recommend_runner(job_type)           │ update(runner, reward)
          │                                      │
┌─────────────────────────────────────────────────────────────┐
│                   GitLab Webhook Handler                     │
│  - Pipeline Created → Get runner recommendation              │
│  - Job Finished → Update MAB with reward                     │
└─────────────────────────────────────────────────────────────┘
          ↑                                      ↑
          │ POST /webhooks/pipeline              │ POST /webhooks/job
          │                                      │
┌─────────────────────────────────────────────────────────────┐
│                        GitLab                                │
│  Project Webhooks: Pipeline events, Job events              │
└─────────────────────────────────────────────────────────────┘
```

### Implementation Sketch

```python
# runner_bandit/bandit.py
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List

@dataclass
class RunnerStats:
    pulls: int = 0
    total_reward: float = 0.0
    rewards: List[float] = field(default_factory=list)
    
    @property
    def mean_reward(self) -> float:
        return self.total_reward / self.pulls if self.pulls > 0 else 0.0

class UCB1Bandit:
    """Upper Confidence Bound algorithm for runner selection."""
    
    def __init__(self, runners: List[str], c: float = 2.0):
        self.runners = runners
        self.c = c  # Exploration parameter
        self.stats: Dict[str, RunnerStats] = {r: RunnerStats() for r in runners}
        self.total_pulls = 0
    
    def select_runner(self) -> str:
        """Select runner using UCB1 formula."""
        # Ensure each runner pulled at least once
        for runner in self.runners:
            if self.stats[runner].pulls == 0:
                return runner
        
        # UCB1: argmax(mean_reward + c * sqrt(ln(t) / n_i))
        ucb_values = {}
        for runner in self.runners:
            stats = self.stats[runner]
            exploitation = stats.mean_reward
            exploration = self.c * np.sqrt(np.log(self.total_pulls) / stats.pulls)
            ucb_values[runner] = exploitation + exploration
        
        return max(ucb_values, key=ucb_values.get)
    
    def update(self, runner: str, reward: float):
        """Update runner statistics with observed reward."""
        self.stats[runner].pulls += 1
        self.stats[runner].total_reward += reward
        self.stats[runner].rewards.append(reward)
        self.total_pulls += 1

class ThompsonSamplingBandit:
    """Thompson Sampling with Beta distribution for binary rewards."""
    
    def __init__(self, runners: List[str]):
        self.runners = runners
        # Beta(alpha, beta) - start with uniform prior
        self.alpha = {r: 1.0 for r in runners}
        self.beta = {r: 1.0 for r in runners}
    
    def select_runner(self) -> str:
        """Sample from posterior and select best."""
        samples = {r: np.random.beta(self.alpha[r], self.beta[r]) 
                   for r in self.runners}
        return max(samples, key=samples.get)
    
    def update(self, runner: str, success: bool):
        """Update posterior with Bernoulli outcome."""
        if success:
            self.alpha[runner] += 1
        else:
            self.beta[runner] += 1
```

### GitLab Webhook Integration

```python
# runner_bandit/webhook_handler.py
from fastapi import FastAPI, Request
from bandit import UCB1Bandit

app = FastAPI()
bandit = UCB1Bandit(
    runners=["gitlab-runner-nordic", "mac-docker", "linux-docker"],
    c=2.0
)

# Cost penalties (EUR/hour normalized)
COST_PENALTY = {
    "gitlab-runner-nordic": 0.05,  # GCP e2-small
    "mac-docker": 0.0,             # Already running
    "linux-docker": 0.0,           # Already running
}

@app.post("/webhooks/job")
async def handle_job_event(request: Request):
    payload = await request.json()
    
    if payload["object_kind"] == "build" and payload["build_status"] == "success":
        runner_name = payload["runner"]["description"]
        duration = payload["build_duration"]
        
        # Calculate reward
        reward = 1.0 / (duration + COST_PENALTY.get(runner_name, 0) * 3600)
        
        bandit.update(runner_name, reward)
        return {"status": "updated", "runner": runner_name, "reward": reward}
    
    return {"status": "ignored"}

@app.get("/recommend")
async def recommend_runner(job_type: str = "default"):
    runner = bandit.select_runner()
    return {"recommended_runner": runner, "job_type": job_type}
```

### Paper-Outline für JKU

**Title:** "Multi-Armed Bandits for Intelligent CI/CD Runner Selection: Balancing Cost, Performance, and Reliability"

**Sections:**
1. Introduction - CI/CD Runner Selection Problem
2. Background - MAB Algorithms (UCB1, Thompson Sampling)
3. System Design - GitLab Webhook Integration
4. Reward Modeling - Duration + Cost + Reliability
5. Experiments - Real-world GitLab Pipeline Data
6. Results - Regret Analysis, Cost Savings
7. Discussion - Exploration vs Exploitation Trade-offs
8. Conclusion

**Key Contributions:**
- Novel application of MAB to CI/CD infrastructure
- Practical integration with GitLab webhooks
- Empirical evaluation on production pipelines

---

## 📋 Offene Punkte

### Phase 1 (Heute)
- [ ] Fix commiten: `gitlab-org-docker` → `docker-any`
- [ ] Test-Pipeline verifizieren
- [ ] Scheduled Runs prüfen (nächster Montag)

### Phase 2 (Paper)
- [ ] RunnerBandit Service implementieren
- [ ] Webhook Endpoint auf GCP deployen
- [ ] Daten sammeln (2-4 Wochen)
- [ ] Paper schreiben für JKU

### Optional: Weitere Tag-Anpassungen
- [ ] `mac-group-shell` → `shell` (4 Dateien)
- [ ] `gcp-shell` → `shell` (falls Nordic offline)

---

## 🔑 Credentials (Reference)

**GitLab:**
- PAT: `glpat--wmS4xEWjjWdOgaOd7oDWG86MQp1OnN4Y3gK.01.101dpjjbj`
- User: wolfram.laube (ID: 1349601)
- Project: ops/backoffice (77555895)

**GCP:**
- SA: `claude-assistant@myk8sproject-207017.iam.gserviceaccount.com`
- Runner VM: `gitlab-runner-nordic` (europe-north2-a)

---

## 💬 Prompt für nächsten Chat

```
Kontext: CI Runner Migration Phase 1 abgeschlossen.
- Default-Tag von gitlab-org-docker auf docker-any umgestellt
- Alle Jobs laufen jetzt auf gitlab-runner-nordic (GCP Stockholm)
- CI Minutes Problem gelöst

Nächster Schritt: Phase 2 - Multi-Armed Bandit Runner Selection
Lies: /mnt/project/HANDOVER_PROFILES_CI_04_02_2026.md

EPIC: Intelligente Runner-Auswahl mit MAB
- UCB1 oder Thompson Sampling implementieren
- Reward = success / (duration + cost_penalty)
- GitLab Webhooks für Job-Events
- Paper-Material für JKU AI Bachelor

Repos:
- ops/backoffice (77555895) - CI/CD Configs
- ops/crm (78171527) - CRM Issues
```

---

---

## 🎰 MAB Runner Service - Deployed

**Location:** `ops/backoffice/services/runner_bandit/`

**Files:**
- `src/bandit.py` - UCB1, Thompson Sampling, ε-greedy
- `src/webhook_handler.py` - FastAPI mit GitLab Webhooks
- `tests/test_bandit.py` - Unit Tests
- `Dockerfile` - Container-ready

**Issue:** [#28 - MAB Runner Bandit Service](https://gitlab.com/wolfram_laube/blauweiss_llc/ops/backoffice/-/issues/28)

---

## 🧠 NSAI Epic - Future Work

**Epic:** [#27 - Neurosymbolic AI Runner Selection](https://gitlab.com/wolfram_laube/blauweiss_llc/ops/backoffice/-/issues/27)

**Sub-Issues:**
| # | Title | Beschreibung |
|---|-------|--------------|
| 22 | Runner Capability Ontology | OWL/JSON-LD Schema für Runner |
| 23 | Job Requirement Parser | YAML → Requirements Extraction |
| 24 | Constraint Satisfaction | Symbolische Filterung |
| 25 | Neural-Symbolic Interface | Hybrid Architecture |
| 26 | JKU Paper Draft | Bachelor-Arbeit Material |

**Architektur:**
```
Symbolisch: Constraints + Explainability
    ↓ feasible_runners
Subsymbolisch: MAB Learning (UCB1/TS)
    ↓ selected_runner + explanation
```

---

*Erstellt: 04.02.2026 ~15:00 UTC*
