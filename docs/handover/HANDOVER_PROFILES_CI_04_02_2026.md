# HANDOVER: Profile-Konsolidierung & CI Runner Migration
**Datum:** 2026-02-04
**Session:** Profile Module Consolidation + CI Discovery

---

## 🎯 Was wurde erreicht

### 1. Profile-Module konsolidiert (Issue #387 ✅)

Zwei parallele Profile-Strukturen wurden in ein einziges Modul zusammengeführt:

**Vorher:**
- `src/admin/applications/pipeline/profiles.py` (~270 Zeilen) - Keyword Matching
- `modules/gmail/profiles.py` + `.yaml` (~130 Zeilen) - Email Generation

**Nachher:**
```
modules/profiles/
├── __init__.py     # Public API + Legacy Compatibility
├── config.yaml     # Single Source of Truth
├── models.py       # Profile/Team Dataclasses
├── loader.py       # YAML Loading
├── matching.py     # Score Calculation
└── README.md       # Documentation
```

**MR !2 merged:** Commit `976ae0ed`

### 2. Test Suite erweitert
- **27 neue Unit Tests** für `modules/profiles/`
- **147 Tests total** passing
- Test-Kategorien: Models, Loader, Matching, Legacy Compatibility

### 3. Backwards Compatibility
Alte Imports funktionieren weiterhin mit Deprecation Warnings:
```python
# Pipeline style (still works)
from src.admin.applications.pipeline.profiles import WOLFRAM, PROFILES
result = WOLFRAM.match_score(text)

# Gmail style (still works)
from modules.gmail.profiles import load_profile
```

---

## 🔴 Entdecktes Problem: CI Minutes erschöpft

Während der Tests wurde festgestellt, dass **Shared Runner CI Minutes erschöpft** sind (`ci_quota_exceeded`).

### Betroffene Jobs (alle ohne `docker-any` Tag)
| Stage | Jobs |
|-------|------|
| `.pre` | `runner-status`, `runner-check`, `gdrive:*`, `gmail:*` |
| `validate` | `mkdocs_nav_check` |
| `test` | `roundtrip:*` |
| `deploy` | `gcp-vm-*`, `gdrive:*`, `gmail:*` |

### Funktionierende Jobs (mit `docker-any` Tag)
| Job | Runner |
|-----|--------|
| `test:unit` | gitlab-runner-nordic ✅ |
| `test:coverage` | gitlab-runner-nordic ✅ |
| `ci_classify` | gitlab-runner-nordic ✅ |

### Verfügbare Runner
| ID | Name | Status | Tags |
|----|------|--------|------|
| 51608579 | gitlab-runner-nordic | ✅ online | `docker-any`, `shell`, `nordic`, `gcp` |
| 51336735 | Mac Docker Runner | ✅ online | (lokal) |
| 51337424 | Mac2 Docker Runner | ✅ online | (lokal) |
| 51337426 | Linux Yoga Docker Runner | ✅ online | (lokal) |

---

## 📋 Neues EPIC: CI Runner Migration

### Ziel
Alle CI Jobs auf eigene Runner umstellen um Shared Runner Minutes zu sparen.

### Scope
1. **Audit:** Alle `.gitlab/*.yml` Dateien identifizieren
2. **Migration:** `tags: [docker-any]` oder `tags: [shell]` zu jedem Job hinzufügen
3. **Test:** Verifizieren dass alle Jobs auf eigenen Runnern laufen
4. **Cleanup:** Ggf. nicht benötigte Jobs deaktivieren

### Betroffene CI-Dateien
```
.gitlab/
├── billing.yml
├── applications.yml
├── pages.yml
├── ci-automation.yml
├── gmail-drafts.yml
├── gdrive-upload.yml
├── runner-fallback.yml
├── gcp-check.yml
├── gcp-setup.yml
├── gcp-migration.yml
├── terraform.yml
├── docker-build.yml
├── k3s-setup.yml
├── infra-setup.yml
├── benchmark.yml
├── fix-shell-runner.yml
├── parallel-jobs.yml
├── tests.yml              ✅ bereits migriert
└── roundtrip-test.yml
```

### Strategie
1. **Default Image ändern** in `.gitlab-ci.yml`:
   ```yaml
   default:
     image: python:3.11-slim
     tags:
       - docker-any  # <-- hinzufügen
   ```
2. **Oder:** Jeden Job einzeln mit `tags:` versehen
3. **Shell Jobs:** `tags: [shell]` für Jobs die Shell-Executor brauchen

---

## 🔧 Aktuelle Infrastruktur

### GCP Runner
- **VM:** `gitlab-runner-nordic`
- **Zone:** europe-north2-a (Stockholm)
- **Type:** e2-small (preemptible)
- **IP:** 34.51.185.83
- **Services:** gitlab-runner, docker, k3s

### Service Accounts
- **Runner Controller:** `gitlab-runner-controller@myk8sproject-207017.iam.gserviceaccount.com`
- **Claude Assistant:** `claude-assistant@myk8sproject-207017.iam.gserviceaccount.com`

---

## 📚 Relevante Commits (diese Session)

```
976ae0ed  Merge branch 'feature/387-consolidate-profiles' (MR !2)
d6f0f814  fix(profiles): add __contains__ and __len__ to legacy dicts
3dfeb16f  ci(tests): add needs:[] to run independently
1b799850  ci(tests): use docker-any tag for own runner
a22011b4  ci(tests): install pyyaml and set PYTHONPATH
b5fee7e7  test(profiles): add comprehensive unit tests
5688a081  refactor(pipeline): deprecate profiles.py
dbea45b5  refactor(gmail): remove profiles.yaml
f6435e3d  refactor(gmail): deprecate profiles.py
a9afba08  feat(profiles): add __init__.py and README.md
d892766d  feat(profiles): add matching.py
625d1cbb  feat(profiles): add loader.py
732c44e7  feat(profiles): add models.py
7414d96a  feat(profiles): add consolidated config.yaml
```

---

## 🔑 Credentials (Reference)

**GitLab:**
- PAT: `glpat--wmS4xEWjjWdOgaOd7oDWG86MQp1OnN4Y3gK.01.101dpjjbj`
- User: wolfram.laube (ID: 1349601)

**GCP:**
- SA: `claude-assistant@myk8sproject-207017.iam.gserviceaccount.com`

**Gmail OAuth:**
- Client ID: `518587440396-vja0emiu68lro97toqguad2no0smlb9e.apps.googleusercontent.com`
- Client Secret: `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`
- Refresh Token: In CI Var (Group-Level, masked)

**CI Variables:**
- Project (backoffice): `GCP_SA_KEY`, `GITLAB_TOKEN`
- Group (blauweiss_llc): `GCP_SERVICE_ACCOUNT_KEY`, `GMAIL_*`

---

## 💬 Prompt für nächsten Chat

```
Kontext: Profile-Modul konsolidiert (MR !2 merged), aber CI Minutes erschöpft.
EPIC: Alle CI Jobs auf eigene Runner migrieren.

Lies bitte: /mnt/project/HANDOVER_PROFILES_CI_04_02_2026.md
(oder im Repo: ops/backoffice/docs/handover/)

Credentials:
- GitLab PAT: glpat--wmS4xEWjjWdOgaOd7oDWG86MQp1OnN4Y3gK.01.101dpjjbj
- User: wolfram.laube (ID: 1349601)
- GCP SA: claude-assistant@myk8sproject-207017.iam.gserviceaccount.com

Problem: Shared Runner CI Minutes erschöpft (ci_quota_exceeded)
Lösung: Alle Jobs auf eigene Runner umstellen

Eigene Runner:
- gitlab-runner-nordic (GCP Stockholm): Tags [docker-any, shell, nordic, gcp]
- Mac/Linux Runner (lokal): Backup

Aufgaben:
1. EPIC Issue erstellen für CI Runner Migration
2. Audit aller .gitlab/*.yml Dateien
3. Migration: Tags hinzufügen (docker-any oder shell)
4. Default-Tags in .gitlab-ci.yml setzen
5. Testen dass alle Jobs auf eigenen Runnern laufen

Repos:
- ops/backoffice (77555895) - Alle Operations
- ops/crm (78171527) - CRM Issues
- ops/corporate (77075415) - ADRs
```
