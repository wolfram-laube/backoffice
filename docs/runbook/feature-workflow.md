# 🚀 Feature Development Workflow

> Deppensicheres HowTo für neue Features - von Idee bis Portal

**Zuletzt verwendet:** NSAI Symbolic Layer (05.02.2026)  
**Dauer:** ~2-3 Stunden für mittleres Feature

---

## Übersicht

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│  1.ADR  │───▶│ 2.Epic  │───▶│ 3.Code  │───▶│ 4.Merge │───▶│ 5.Docs  │
│         │    │ Issues  │    │ Tests   │    │ Close   │    │ Portal  │
└─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘
```

---

## Phase 1: ADR erstellen (ops/corporate)

### Wann?
- Neue Architektur-Entscheidung
- Signifikante technische Änderung
- Etwas das man später erklären muss

### Schritte

```bash
# 1. Template holen
curl -s --header "PRIVATE-TOKEN: $PAT" \
  "https://gitlab.com/api/v4/projects/77075415/repository/files/docs%2Fadr%2F_template.md/raw?ref=main"

# 2. ADR schreiben mit:
#    - Context (Problem)
#    - Decision (Lösung)
#    - Consequences (Pros/Cons)
#    - Alternatives Considered

# 3. Prefix wählen:
#    - GOV-xxx: Governance (org-wide)
#    - OPS-xxx: Operations (billing, crm)
#    - AI-xxx:  AI/ML
#    - INF-xxx: Infrastructure

# 4. Committen nach docs/adr/{prefix}/
# 5. Index updaten: docs/adr/index.md
```

### Checkliste ADR
- [ ] Status: `Proposed`
- [ ] Datum gesetzt
- [ ] Author eingetragen
- [ ] Tags vergeben
- [ ] Alternativen dokumentiert
- [ ] Index aktualisiert

---

## Phase 2: Epic & Issues anlegen (ops/backoffice)

### Epic erstellen

```bash
curl -s --request POST \
  --header "PRIVATE-TOKEN: $PAT" \
  --header "Content-Type: application/json" \
  --data '{
    "title": "[EPIC] Feature Name",
    "description": "## Vision\n\n...\n\n## Related Issues\n\n- #xx\n- #yy",
    "labels": "epic,feature-area"
  }' \
  "https://gitlab.com/api/v4/projects/77555895/issues"
```

### Sub-Issues erstellen

```bash
# Pro Arbeitspaket ein Issue
curl -s --request POST \
  --header "PRIVATE-TOKEN: $PAT" \
  --header "Content-Type: application/json" \
  --data '{
    "title": "[PREFIX] Specific Task",
    "description": "## Goal\n\n## Acceptance Criteria\n\n- [ ] ...",
    "labels": "feature-area"
  }' \
  "https://gitlab.com/api/v4/projects/77555895/issues"
```

### Checkliste Issues
- [ ] Epic mit Vision & Übersicht
- [ ] Sub-Issues für jedes Arbeitspaket
- [ ] Labels vergeben
- [ ] Issues im Epic verlinkt

---

## Phase 3: Feature Branch & Code

### Branch erstellen

```bash
curl -s --request POST \
  --header "PRIVATE-TOKEN: $PAT" \
  --data '{"branch": "feature/my-feature", "ref": "main"}' \
  "https://gitlab.com/api/v4/projects/77555895/repository/branches"
```

### Naming Conventions

| Typ | Branch Name | Beispiel |
|-----|-------------|----------|
| Feature | `feature/name` | `feature/nsai-symbolic-layer` |
| Bugfix | `fix/issue-name` | `fix/parser-timeout` |
| Hotfix | `hotfix/description` | `hotfix/ci-runner` |

### Code committen

```bash
# Mit Issue-Referenz!
curl -s --request POST \
  --header "PRIVATE-TOKEN: $PAT" \
  --data '{
    "branch": "feature/my-feature",
    "commit_message": "feat(module): Add feature X (#123)\n\nDetails...",
    "actions": [...]
  }' \
  "https://gitlab.com/api/v4/projects/77555895/repository/commits"
```

### Commit Message Format

```
type(scope): Short description (#issue)

Longer description if needed.

Related: #epic, #other-issue
```

**Types:** `feat`, `fix`, `docs`, `test`, `refactor`, `ci`, `chore`

### Checkliste Code
- [ ] Feature Branch erstellt
- [ ] Issues auf `in-progress` gesetzt
- [ ] Code mit Docstrings
- [ ] Tests geschrieben (pytest)
- [ ] Commit Messages mit Issue-Referenz

---

## Phase 4: Tests & MR

### Tests lokal prüfen

```bash
cd services/my-service
pytest tests/ -v --tb=short
```

### CI Config (wenn neuer Service)

```yaml
# .gitlab/my-service-tests.yml
test:my-service:unit:
  extends: .test-base
  rules:
    - changes:
        - services/my-service/**/*
  script:
    - pytest services/my-service/tests/ -v
```

### Merge Request erstellen

```bash
curl -s --request POST \
  --header "PRIVATE-TOKEN: $PAT" \
  --data '{
    "source_branch": "feature/my-feature",
    "target_branch": "main",
    "title": "feat(scope): Description",
    "description": "## Summary\n\n## Issues\n\nCloses #x, #y, #z",
    "remove_source_branch": true
  }' \
  "https://gitlab.com/api/v4/projects/77555895/merge_requests"
```

### Pipeline triggern

```bash
curl -s --request POST \
  --header "PRIVATE-TOKEN: $PAT" \
  --data '{"ref": "feature/my-feature", "variables": [{"key": "RUN_TESTS", "value": "true"}]}' \
  "https://gitlab.com/api/v4/projects/77555895/pipeline"
```

### Checkliste MR
- [ ] Tests grün in CI
- [ ] MR Description mit Summary
- [ ] Issues verlinkt (Closes #xx)
- [ ] `remove_source_branch: true`

---

## Phase 5: Merge & Cleanup

### MR mergen (wenn Tests grün)

```bash
curl -s --request PUT \
  --header "PRIVATE-TOKEN: $PAT" \
  --data '{"should_remove_source_branch": true}' \
  "https://gitlab.com/api/v4/projects/77555895/merge_requests/{iid}/merge"
```

### Issues schließen

```bash
for issue_id in 22 23 24; do
  curl -s --request PUT \
    --header "PRIVATE-TOKEN: $PAT" \
    --data '{"state_event": "close", "add_labels": "done"}' \
    "https://gitlab.com/api/v4/projects/77555895/issues/$issue_id"
done
```

### Epic updaten

```bash
curl -s --request POST \
  --header "PRIVATE-TOKEN: $PAT" \
  --data '{"body": "## ✅ Phase X Complete\n\n- MR !x merged\n- Issues closed"}' \
  "https://gitlab.com/api/v4/projects/77555895/issues/{epic_id}/notes"
```

### ADR Status → Accepted

```bash
# In ops/corporate: Status von "Proposed" auf "Accepted" ändern
# Index updaten
```

### Checkliste Cleanup
- [ ] MR gemerged
- [ ] Branch gelöscht
- [ ] Issues geschlossen + `done` Label
- [ ] Epic mit Progress Note
- [ ] ADR → Accepted

---

## Phase 6: Dokumentation & Portal

### Service README

```markdown
# Service Name

> One-line description

## Quick Start
## API
## Testing
## Related
```

### Portal Docs (docs/services/)

```markdown
# 🎯 Service Name

**Status:** ✅ Implemented
**ADR:** [XX-001](link)
**Epic:** [#nn](link)

## Architecture
## Usage
## Issues & Progress
```

### mkdocs.yml updaten

```yaml
nav:
  - "🧠 Services":
    - "My Service": services/my-service.md  # ← Hinzufügen
```

### Checkliste Docs
- [ ] services/xxx/README.md
- [ ] docs/services/xxx.md
- [ ] mkdocs.yml nav aktualisiert
- [ ] Pages Pipeline getriggert

---

## Quick Reference

### Projekt IDs

| Repo | ID |
|------|----|
| ops/backoffice | 77555895 |
| ops/corporate | 77075415 |
| ops/crm | 78171527 |

### Labels

| Label | Bedeutung |
|-------|-----------|
| `epic` | Übergeordnetes Issue |
| `in-progress` | Wird bearbeitet |
| `done` | Abgeschlossen |
| `ai/ml` | AI/ML bezogen |
| `jku-bachelor` | Paper-relevant |

### API Shortcuts

```bash
# Issues auflisten
curl -s -H "PRIVATE-TOKEN: $PAT" \
  "https://gitlab.com/api/v4/projects/77555895/issues?state=opened"

# Branch Status
curl -s -H "PRIVATE-TOKEN: $PAT" \
  "https://gitlab.com/api/v4/projects/77555895/repository/branches/feature%2Fmy-feature"

# Pipeline Jobs
curl -s -H "PRIVATE-TOKEN: $PAT" \
  "https://gitlab.com/api/v4/projects/77555895/pipelines/{id}/jobs"
```

---

## Beispiel: NSAI Symbolic Layer

| Phase | Aktion | Ergebnis |
|-------|--------|----------|
| 1. ADR | AI-001 erstellt | docs/adr/ai/AI-001-...md |
| 2. Epic | #27 + #22-26 | 6 Issues angelegt |
| 3. Code | 14 Files, 1400 LOC | services/nsai/ |
| 4. Tests | 46 Tests | CI grün |
| 5. Merge | MR !3 | 8ee78e5d |
| 6. Docs | README + Portal | docs/services/nsai.md |

**Dauer:** ~2.5 Stunden

---

## Troubleshooting

### Pipeline failed?
```bash
# Job Log holen
curl -s -H "PRIVATE-TOKEN: $PAT" \
  "https://gitlab.com/api/v4/projects/77555895/jobs/{job_id}/trace" | tail -50
```

### Merge Conflicts?
```bash
# Rebase auf main
git fetch origin
git rebase origin/main
# Oder via API: MR löschen, neu erstellen
```

### Pages nicht aktualisiert?
```bash
# Manuell triggern
curl -s --request POST -H "PRIVATE-TOKEN: $PAT" \
  -d '{"ref": "main"}' \
  "https://gitlab.com/api/v4/projects/77555895/pipeline"
```
