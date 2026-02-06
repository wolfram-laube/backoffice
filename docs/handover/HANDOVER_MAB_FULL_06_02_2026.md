# HANDOVER: MAB Runner Integration (Full Session)

**Datum:** 2026-02-06
**Session:** MAB CI Runner Integration — GCS Persistence, Availability, Auto-Start/Stop
**Context:** Portal & Billing fertig → dynamische Runner-Auswahl als nächster Schritt

---

## 🎯 Executive Summary

MAB Service von statischer Runner-Empfehlung zu **availability-aware, self-managing** System erweitert:

1. ✅ **GCS Persistence** — Observations überleben Cloud Run Cold-Starts
2. ✅ **6 Runner** — 4 Docker + 2 K8s (Mac#1, Mac#2) als Arms
3. ✅ **Webhooks auf 3 Repos** — Backoffice, Portal, CLARISSA lernen passiv
4. ✅ **Availability-Check** — `/recommend` prüft welche Runner online sind
5. ✅ **GCP Auto-Start** — Kein Runner da? VM startet automatisch
6. ✅ **GCP Auto-Stop** — VM fährt nach 5 Min Idle wieder runter (nur wenn MAB sie gestartet hat)

---

## 📊 MAB Service v0.3.1

**URL:** https://runner-bandit-m5cziijwqa-lz.a.run.app/

| Endpoint | Methode | Beschreibung |
|----------|---------|-------------|
| `/` | GET | Service Info + Features |
| `/recommend` | GET | Runner-Empfehlung (availability-aware) |
| `/update` | POST | Feedback nach Job |
| `/webhooks/gitlab` | POST | GitLab Webhook Handler |
| `/stats` | GET | Detaillierte Statistiken + Ranking |
| `/availability` | GET | Welche Runner sind gerade online? |
| `/vm/start` | POST | GCP VM manuell starten |
| `/vm/stop` | POST | GCP VM manuell stoppen |
| `/vm/status` | GET | VM Status + Lifecycle Info |
| `/health` | GET | Health Check |
| `/reset` | POST | Stats zurücksetzen |

### /recommend Flow

```
GET /recommend
  → GitLab API: Welche Runner online?
  → Online > 0? → MAB wählt aus Online-Pool (UCB1)
  → Online = 0? → GCP VM starten
                → Nordic optimistisch empfehlen
                → Auto-Stop Timer nach letztem Job (5 Min)
```

### Auto-Stop Logik

```
MAB startet VM → lifecycle.auto_started = true
  → Jobs laufen → Timer pausiert
  → Letzter Job fertig → 5 Min Timer
  → Neuer Job? → Timer cancelled
  → Timeout? → VM stop → lifecycle.reset()

VM war schon an? → lifecycle.auto_started = false → kein Auto-Stop
```

---

## 📁 Commits dieser Session

| Commit | Beschreibung |
|--------|-------------|
| `0981db9d` | GCS Persistence + `.mab-enabled` CI Template + mab:recommend/stats Jobs |
| `08d690cb` | Handover + INDEX Update |
| `b9fe480e` | Mac K8s Runner (#1 + #2) als Arms ins MAB |
| `a9bf2817` | Availability-Check + GCP Auto-Start + `/availability`, `/vm/*` Endpoints |
| `32c392b1` | VM Lifecycle Auto-Stop nach Idle Timeout |

### Neue Dateien

| Datei | Beschreibung |
|-------|-------------|
| `services/runner_bandit/src/availability.py` | Runner-Availability via GitLab API + GCP VM Control |
| `services/runner_bandit/src/vm_lifecycle.py` | Auto-Stop Lifecycle Manager (Timer-basiert) |
| `.gitlab/mab-integration.yml` | CI Templates: `.mab-enabled`, `mab:recommend`, `mab:stats` |
| `scripts/mab_report.sh` | Standalone after_script Reporter |
| `scripts/mab_recommend.sh` | Standalone dotenv Generator |

### Geänderte Dateien

| Datei | Änderung |
|-------|---------|
| `services/runner_bandit/src/bandit.py` | GCS StateBackend + Factory + 6 Runner |
| `services/runner_bandit/src/webhook_handler.py` | v0.3.1: Availability + Lifecycle |
| `services/runner_bandit/requirements.txt` | +google-cloud-storage, +google-cloud-compute |
| `services/runner_bandit/Dockerfile` | GCS/GCP env vars |
| `.gitlab-ci.yml` | include mab-integration.yml |
| `.gitlab/cloud-run.yml` | Deploy mit GCS + GitLab Token + GCP env vars |

---

## 🏗️ Infrastruktur

### GCS Bucket

- **Name:** `gs://blauweiss-mab-state`
- **Location:** `europe-north1`
- **Blob:** `bandit_state.json`
- **IAM:** `gitlab-runner-controller@` + `claude-assistant@` → `storage.objectAdmin`

### GCP Compute Permissions

- **SA:** `gitlab-runner-controller@myk8sproject-207017.iam.gserviceaccount.com`
- **Permissions:** `compute.instances.get`, `.start`, `.stop` ✅

### Webhooks

| Repo | Project ID | Webhook ID |
|------|-----------|------------|
| Backoffice | 77555895 | 69840788 |
| Portal | 78288201 | 69912322 |
| CLARISSA | 77260390 | 69912323 |

### Runner Tags (MAB Mapping)

| Runner | Tags | MAB Tag | Executor |
|--------|------|---------|----------|
| gitlab-runner-nordic | docker-any, shell, nordic, gcp | nordic | Docker |
| Mac Docker Runner | mac-docker, docker-any, mac-any | mac-docker | Docker |
| Mac2 Docker Runner | mac2-docker, docker-any, mac-any | mac2-docker | Docker |
| Linux Yoga Docker Runner | linux-docker, docker-any, linux-any | linux-docker | Docker |
| Mac K8s Runner | mac-k8s, k8s-any, mac-any | mac-k8s | Kubernetes |
| Mac2 K8s Runner | mac2-k8s, k8s-any, mac-any | mac2-k8s | Kubernetes |

---

## ⚠️ OFFEN: Cloud Run Deploy

**Der Service läuft noch auf v0.1.0!** Alle Code-Änderungen sind committed, aber noch nicht deployed.

Mehrere Deploy-Pipelines getriggert (#2310387470, #2310468512), `cloud-run:build` + `cloud-run:deploy` stehen auf `created`.

### Deploy manuell anstoßen

```bash
# Option 1: Pipeline triggern
curl --request POST \
  --header "PRIVATE-TOKEN: glpat-..." \
  --data '{"ref":"main","variables":[{"key":"CLOUD_RUN_DEPLOY","value":"true"}]}' \
  "https://gitlab.com/api/v4/projects/77555895/pipeline"

# Option 2: Jobs manuell starten
# In GitLab UI → Pipeline → cloud-run:build → Play → cloud-run:deploy → Play
```

### Nach Deploy verifizieren

```bash
# Sollte v0.3.1 zeigen + 6 Runner + GCS persistence
curl https://runner-bandit-m5cziijwqa-lz.a.run.app/

# Availability-Check testen
curl https://runner-bandit-m5cziijwqa-lz.a.run.app/availability

# VM Status
curl https://runner-bandit-m5cziijwqa-lz.a.run.app/vm/status
```

---

## 📋 Nächste Schritte

1. **Cloud Run Deploy** durchbringen (Prio 1)
2. **`.mab-enabled` auf Key-Jobs** anwenden (billing, tests, pages)
3. **Parent-Child Pipeline** für echte dynamische Tag-Selektion
4. **MAB Dashboard** im Portal (MkDocs Page mit Stats)
5. **GCP_IDLE_SHUTDOWN_SECONDS** tunen (aktuell 5 Min)
6. **NSAI Epic #27** — Symbolische Constraints als Erweiterung

---

## 🔑 Credentials

```
GitLab PAT: glpat--wmS4xEWjjWdOgaOd7oDWG86MQp1OnN4Y3gK.01.101dpjjbj
GCP Project: myk8sproject-207017
GCS Bucket: blauweiss-mab-state
MAB Service: https://runner-bandit-m5cziijwqa-lz.a.run.app/
Backoffice: 77555895
Portal: 78288201
CLARISSA: 77260390
```

## Keywords

mab, multi-armed-bandit, ucb1, runner, ci, integration, webhook, gcs, cloud-run, availability, auto-start, auto-stop, vm-lifecycle, k8s, kubernetes, gcp
