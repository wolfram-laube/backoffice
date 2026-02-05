# 🎰 Handover: MAB Service Cloud Run Deployment

**Datum:** 05.02.2026  
**Session:** MAB Service Cloud Run Deployment & Webhook Integration  
**Status:** ✅ Abgeschlossen

---

## Zusammenfassung

Multi-Armed Bandit (MAB) Service erfolgreich auf GCP Cloud Run deployed und mit GitLab Webhook integriert. Der Service sammelt aktiv Job-Performance-Daten für die NSAI Runner Selection Forschung.

---

## Was wurde erreicht

### 1. Cloud Run Deployment ✅
- **Service URL:** https://runner-bandit-m5cziijwqa-lz.a.run.app
- **Region:** europe-north1
- **Image:** `europe-north1-docker.pkg.dev/myk8sproject-207017/blauweiss/runner-bandit`

### 2. CI/CD Pipeline ✅
```
GitLab Registry → skopeo copy → GCP Artifact Registry → Cloud Run
```

**Pipeline File:** `.gitlab/cloud-run.yml`
- `cloud-run:build` - Kaniko → GitLab Registry
- `cloud-run:copy` - skopeo → GCP Artifact Registry
- `cloud-run:deploy` - gcloud → Cloud Run

**Trigger:** Manual oder changes zu `services/runner_bandit/**`

### 3. GitLab Webhook ✅
- **Webhook ID:** 69840788
- **Events:** Job Events
- **Endpoint:** `/webhooks/gitlab`
- **Status:** Aktiv, sammelt Daten

### 4. Branch Protection ✅
`main` Branch ist jetzt geschützt:
- **Push:** No one (nur via MR)
- **Merge:** Maintainers only

### 5. Dokumentation ✅
- `docs/runbook/git-workflow.md` - Kanonischer Git Workflow
- `docs/services/nsai.md` - Updated mit Deployment-Status
- `services/runner_bandit/README.md` - Komplett überarbeitet

### 6. Tests ✅
- `tests/test_bandit.py` - 7 Algorithm-Tests
- `tests/test_api.py` - 11 API-Integration-Tests

---

## GCP IAM Konfiguration

Der `gitlab-runner-controller` Service Account hat folgende Rollen erhalten:

| Rolle | Zweck |
|-------|-------|
| `roles/run.admin` | Cloud Run Deploy |
| `roles/storage.admin` | Container Registry |
| `roles/artifactregistry.admin` | Artifact Registry (createOnPush) |
| `roles/iam.serviceAccountUser` | Act as compute SA |

---

## Service Endpoints

| Endpoint | Method | Beschreibung |
|----------|--------|--------------|
| `/` | GET | Health check, Service info |
| `/recommend` | GET | Runner-Empfehlung (UCB1) |
| `/stats` | GET | Aktuelle Statistiken |
| `/update` | POST | Manuelle Observation |
| `/webhooks/gitlab` | POST | GitLab Webhook Handler |
| `/reset` | POST | Statistiken zurücksetzen |

---

## Aktuelle Statistiken

```json
{
  "algorithm": "UCB1Bandit",
  "total_observations": 3,
  "runners": {
    "gitlab-runner-nordic": {
      "pulls": 3,
      "mean_reward": 2.08,
      "success_rate": 1.0,
      "avg_duration": 25.02
    }
  }
}
```

---

## Merge Requests

| MR | Status | Beschreibung |
|----|--------|--------------|
| !4 | Closed | Ersetzt durch !5 (Konflikte) |
| !5 | Pending | Cloud Run Pipeline (auto-merge) |
| !6 | Merged | Git Workflow Docs |
| !7 | Merged | API Tests & README |

---

## Offene Punkte

### Kurzfristig
- [ ] MR !5 mergen (wartet auf CI)

### Mittelfristig (2-4 Wochen)
- [ ] Daten sammeln für Paper-Analyse
- [ ] UCB1 vs Thompson Sampling vs ε-greedy Vergleich
- [ ] Regret-Analyse

### Langfristig (Q1 2026)
- [ ] NSAI Epic #27 - Neural-Symbolic Interface
- [ ] JKU Bachelor Paper Draft (#26)
- [ ] Integration: CSP → MAB → Optimal Runner

---

## Wichtige Links

| Resource | URL |
|----------|-----|
| MAB Service | https://runner-bandit-m5cziijwqa-lz.a.run.app |
| NSAI Docs | https://wolfram_laube.gitlab.io/blauweiss_llc/ops/backoffice/services/nsai/ |
| Git Workflow | https://wolfram_laube.gitlab.io/blauweiss_llc/ops/backoffice/runbook/git-workflow/ |
| Epic #27 | https://gitlab.com/blauweiss_llc/ops/backoffice/-/issues/27 |
| Pipeline Config | `.gitlab/cloud-run.yml` |

---

## Lessons Learned

1. **Branch Protection früh aktivieren** - Konflikte durch direkte main-Commits vermeidbar
2. **GCP IAM Propagation** - Kann bis zu 5 Minuten dauern
3. **Cloud Run + GitLab Registry** - Nicht direkt möglich, braucht Zwischenschritt (skopeo)
4. **GCR → Artifact Registry** - Google hat GCR auf AR umgestellt, `createOnPush` Permission nötig

---

## Nächste Session

**Titel:** NSAI Neural-Symbolic Interface Implementation

**Fokus:**
- Issue #25: Neural-Symbolic Interface
- MAB in CSP Solver integrieren
- Feasible Set → MAB → Optimal Runner
