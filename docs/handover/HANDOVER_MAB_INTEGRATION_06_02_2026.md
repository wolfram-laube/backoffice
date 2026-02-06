# HANDOVER: MAB Runner Integration

**Datum:** 2026-02-06
**Session:** MAB (Multi-Armed Bandit) CI Runner Integration
**Context:** Portal & Billing fertig, dynamische Runner-Auswahl als nächster Schritt

---

## 🎯 Executive Summary

**Ziel:** CI Jobs fragen MAB Service nach optimaler Runner-Empfehlung, Tags werden dynamisch gesetzt.

**Ergebnis:** 3-Phasen-Integration implementiert:
1. ✅ **Passive Learning** (Webhooks) → MAB lernt aus allen Jobs automatisch
2. ✅ **Active Reporting** (`.mab-enabled` Template) → Jobs reporten Ergebnis direkt
3. 🔧 **Dynamic Selection** (`mab:recommend`) → Parent-Child Pipeline mit MAB-Tag

---

## 📊 Aktueller Stand

### MAB Service (v0.2.0)

| Endpoint | Beschreibung | Status |
|----------|-------------|--------|
| `/` | Service Info | ✅ |
| `/recommend` | Runner-Empfehlung (inkl. Tag) | ✅ |
| `/update` | Feedback nach Job | ✅ |
| `/webhooks/gitlab` | GitLab Webhook Handler | ✅ |
| `/stats` | Detaillierte Statistiken | ✅ |
| `/health` | Health Check | ✅ |
| `/reset` | Stats zurücksetzen | ✅ |

**URL:** https://runner-bandit-m5cziijwqa-lz.a.run.app/

### State Persistence

| Backend | Beschreibung | Status |
|---------|-------------|--------|
| GCS | `gs://blauweiss-mab-state/bandit_state.json` | ✅ Bucket erstellt |
| Local | `/tmp/bandit_state.json` (Fallback) | ✅ |

**WICHTIG:** GCS Persistence wird erst aktiv nach Cloud Run Redeploy (Pipeline #2310387470).
Bis dahin nutzt der Service lokalen Speicher (geht bei Cold Start verloren).

### Webhooks (Passive Learning)

| Repo | Project ID | Webhook ID | Status |
|------|-----------|------------|--------|
| Backoffice | 77555895 | 69840788 | ✅ aktiv, sammelt Daten |
| Portal | 78288201 | 69912322 | ✅ neu erstellt |
| CLARISSA | 77260390 | 69912323 | ✅ neu erstellt |

### Runner Tag-Mapping

| Runner | GitLab Tag | MAB Tag | Status |
|--------|-----------|---------|--------|
| gitlab-runner-nordic | docker-any, nordic | nordic | ✅ online |
| Mac Docker Runner | docker-any, mac-docker | mac-docker | ✅ online |
| Mac2 Docker Runner | docker-any, mac2-docker | mac2-docker | ✅ online |
| Linux Yoga Docker Runner | docker-any, linux-docker | linux-docker | ✅ online |

---

## 🏗️ Architektur

```
┌─────────────────────────────────────────────────────────────┐
│  GitLab CI Pipeline                                          │
│                                                              │
│  ┌──────────┐    ┌──────────────┐    ┌─────────────────┐   │
│  │ .pre     │───→│ mab:recommend│───→│ dotenv: mab.env │   │
│  │ Stage    │    │ (optional)   │    │ MAB_RUNNER_TAG   │   │
│  └──────────┘    └──────────────┘    └─────────────────┘   │
│                                              │               │
│  ┌──────────────────────────────────────────┴──────────┐   │
│  │  Subsequent Jobs (extends: .mab-enabled)             │   │
│  │  - Uses MAB_RUNNER_TAG if available                  │   │
│  │  - after_script → POST /update with job outcome      │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                          │ Webhook                │ /update
                          ▼                        ▼
┌─────────────────────────────────────────────────────────────┐
│  Runner Bandit Service (Cloud Run)                           │
│  ┌───────────┐  ┌──────────┐  ┌────────────────────────┐   │
│  │ UCB1      │  │ GCS      │  │ Webhook Handler        │   │
│  │ Algorithm │  │ Backend  │  │ (job_events → update)  │   │
│  └───────────┘  └──────────┘  └────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
         ▲                ▼
         │     gs://blauweiss-mab-state/
         │     bandit_state.json
         └──── (persists across restarts)
```

---

## 📁 Neue/Geänderte Dateien

### Commit `0981db9d`

| Datei | Aktion | Beschreibung |
|-------|--------|-------------|
| `services/runner_bandit/src/bandit.py` | UPDATE | GCS StateBackend + Factory Pattern |
| `services/runner_bandit/src/webhook_handler.py` | UPDATE | v0.2.0: recommended_tag, /health, /stats ranking |
| `services/runner_bandit/requirements.txt` | UPDATE | +google-cloud-storage |
| `services/runner_bandit/Dockerfile` | UPDATE | BANDIT_GCS_BUCKET env |
| `.gitlab/mab-integration.yml` | NEW | .mab-enabled template + mab:recommend/stats jobs |
| `scripts/mab_report.sh` | UPDATE | after_script MAB reporter |
| `scripts/mab_recommend.sh` | UPDATE | dotenv artifact generator |
| `.gitlab-ci.yml` | UPDATE | include mab-integration.yml |
| `.gitlab/cloud-run.yml` | UPDATE | +BANDIT_GCS_BUCKET env var |

---

## 🚀 Deployment

### Pending: Cloud Run Redeploy

Pipeline **#2310387470** enthält `cloud-run:build` und `cloud-run:deploy`.

**Manueller Deploy falls Pipeline blockiert:**
```bash
# Trigger via API
curl --request POST \
  --header "PRIVATE-TOKEN: $PAT" \
  --header "Content-Type: application/json" \
  --data '{"ref":"main","variables":[{"key":"CLOUD_RUN_DEPLOY","value":"true"}]}' \
  "https://gitlab.com/api/v4/projects/77555895/pipeline"
```

**Oder direkt via gcloud:**
```bash
gcloud run deploy runner-bandit \
  --image=europe-north1-docker.pkg.dev/myk8sproject-207017/backoffice/runner-bandit:latest \
  --region=europe-north1 \
  --set-env-vars=BANDIT_ALGORITHM=ucb1,BANDIT_GCS_BUCKET=blauweiss-mab-state
```

### GCS Bucket

- **Name:** `blauweiss-mab-state`
- **Location:** `europe-north1`
- **IAM:** `gitlab-runner-controller@` und `claude-assistant@` haben `storage.objectAdmin`
- **ACHTUNG:** Cloud Run SA braucht evtl. noch Zugriff → bei Deploy prüfen!

---

## 🔄 Integration Guide

### Minimal: Job mit MAB Reporting

```yaml
my-job:
  extends: .mab-enabled
  script:
    - echo "My work here"
  # after_script wird automatisch von .mab-enabled hinzugefügt
```

### Advanced: MAB-gesteuerte Runner-Auswahl

```yaml
# Phase 1: Get recommendation
select-runner:
  stage: .pre
  extends: .mab-recommend  # Not yet implemented - TODO
  artifacts:
    reports:
      dotenv: mab.env

# Phase 2: Use recommendation
build:
  stage: build
  tags:
    - $MAB_RUNNER_TAG  # Dynamic! Requires GitLab 15.7+
  needs: [select-runner]
  script:
    - echo "Running on MAB-selected runner"
```

**⚠️ Limitation:** GitLab CI `tags:` unterstützt keine Variablen-Expansion in allen Versionen.
Alternative: Parent-Child Pipeline mit `trigger:` und `strategy: depend`.

---

## 📈 MAB Algorithmus-Details

### UCB1 (Upper Confidence Bound)

```
UCB1(runner) = mean_reward + c * sqrt(ln(t) / n_i)

wobei:
  mean_reward = durchschnittlicher Reward des Runners
  c = 2.0 (Exploration-Parameter)
  t = Gesamtzahl Beobachtungen
  n_i = Beobachtungen für diesen Runner
```

### Reward-Funktion

```
reward = success / (duration_min + cost_penalty + 0.1)

wobei:
  success ∈ {0, 1}
  duration_min = Job-Dauer in Minuten
  cost_penalty = Runner-Kosten * (Dauer/3600)
```

### Verhalten

- **Exploration:** UCB1 probiert zunächst alle Runner aus (pulls=0 → höchste Priorität)
- **Exploitation:** Nach ausreichend Daten bevorzugt UCB1 den Runner mit bestem Reward
- **Aktuell:** Nordic hat 7 pulls, rest noch 0 → UCB1 exploriert die lokalen Runner

---

## 📋 Offene Themen

1. **Cloud Run Redeploy** mit GCS Backend (Pipeline #2310387470 oder manuell)
2. **Cloud Run SA Zugriff** auf GCS Bucket prüfen nach Deploy
3. **`.mab-enabled` auf Key-Jobs** anwenden (billing, tests, pages)
4. **Parent-Child Pipeline** für echte dynamische Tag-Selektion (Phase 3)
5. **Dashboard** in Portal integrieren (MAB Stats als MkDocs Page)
6. **NSAI Epic #27** - Symbolische Constraints als Erweiterung (Future Work)

---

## 🔑 Credentials & Access

```
GitLab PAT: glpat--wmS4xEWjjWdOgaOd7oDWG86MQp1OnN4Y3gK.01.101dpjjbj
GCP Project: myk8sproject-207017
GCS Bucket: blauweiss-mab-state
MAB Service: https://runner-bandit-m5cziijwqa-lz.a.run.app/
Backoffice: 77555895
Portal: 78288201
CLARISSA: 77260390
```

---

## Keywords

mab, multi-armed-bandit, ucb1, runner, ci, integration, webhook, gcs, cloud-run, tags, dynamic, selection
