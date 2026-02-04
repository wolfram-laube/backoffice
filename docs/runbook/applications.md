# Applications Runbook

> Vom Jobportal zur Bewerbung - automatisiert.

---

## Quick Reference

| Item | Value |
|------|-------|
| **Repo** | projects/clarissa (→ backoffice nach Migration) |
| **Pipeline** | `.gitlab/applications.yml` |
| **Schedule** | #4125172 (Mo-Fr 08:00) |
| **CRM Board** | https://gitlab.com/wolfram_laube/blauweiss_llc/ops/crm/-/boards/10081703 |
| **Profile** | `attachments/Profil_Laube_w_Summary_DE.pdf` |
| **Owner** | Wolfram |

---

## Übersicht: Die Application Pipeline

```
┌────────────────────────────────────────────────────────────────┐
│                    APPLICATIONS PIPELINE                       │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  1. CRAWL (applications_crawl.py)                             │
│     └─▶ Freelancermap, GULP, etc. scrapen                     │
│     └─▶ Neue Projekte in JSON speichern                       │
│                                                                │
│  2. MATCH (applications_match.py)                             │
│     └─▶ LLM bewertet Match gegen Profile                      │
│     └─▶ Score 0-100% pro Projekt                              │
│     └─▶ Filtert < 70% raus                                    │
│                                                                │
│  3. DRAFT (applications_drafts.py)                            │
│     └─▶ Generiert personalisierte Bewerbungstexte            │
│     └─▶ Erstellt Gmail-Entwürfe                              │
│                                                                │
│  4. CRM UPDATE                                                │
│     └─▶ Neues Issue pro Bewerbung                            │
│     └─▶ Labels: status::neu, rate::X, tech::Y                │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

---

## Teil 1: Automatischer Modus

### Was passiert täglich (Mo-Fr 08:00)

1. **Crawl:** Neue Projekte von freelancermap werden geholt
2. **Match:** LLM (Claude) bewertet gegen Wolfram-Profil
3. **Filter:** Projekte mit Match ≥70% gehen weiter
4. **Draft:** Gmail-Entwürfe werden erstellt
5. **CRM:** Issues werden angelegt

### Ergebnis prüfen

**Gmail:** Drafts erscheinen in `wolfram.laube@blauweiss-edv.at`

**CRM Board:** Neue Issues in Spalte "Neu"
→ https://gitlab.com/wolfram_laube/blauweiss_llc/ops/crm/-/boards/10081703

---

## Teil 2: Manueller Modus

### Nur Crawl (neue Projekte holen)

```bash
curl -X POST \
  -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"ref":"main","variables":[{"key":"CRAWL_ONLY","value":"true"}]}' \
  "https://gitlab.com/api/v4/projects/77260390/pipeline"
```

### Nur Match (ohne Crawl)

```bash
curl -X POST \
  -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"ref":"main","variables":[{"key":"MATCH_ONLY","value":"true"}]}' \
  "https://gitlab.com/api/v4/projects/77260390/pipeline"
```

### Für bestimmtes Profil (Team-Modus)

```bash
# Für Ian
curl -X POST \
  -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  -d '{"ref":"main","variables":[{"key":"PROFILE","value":"ian"}]}' \
  "https://gitlab.com/api/v4/projects/77260390/pipeline"
```

---

## Teil 3: Profile

### Verfügbare Profile

| Person | Datei | Schwerpunkt |
|--------|-------|-------------|
| **Wolfram** | `Profil_Laube_w_Summary_DE.pdf` | DevOps, Cloud, K8s |
| **Ian** | `CV_Ian_Matejka_DE.pdf` | AI/ML, Python |
| **Michael** | `CV_Michael_Matejka_DE.pdf` | PM, Business |

### Profil aktualisieren

1. Neue PDF in `attachments/` committen
2. `config/profiles.yaml` anpassen (falls Dateiname geändert)
3. Pipeline läuft automatisch mit neuem Profil

---

## Teil 4: Matching-Logik

### Bewertungskriterien

| Kriterium | Gewicht | Beschreibung |
|-----------|---------|--------------|
| **Tech Stack** | 40% | Übereinstimmung der Technologien |
| **Erfahrung** | 25% | Jahre, Seniorität |
| **Domain** | 20% | Branche (Energie, Banking, etc.) |
| **Remote** | 10% | Remote-Anteil |
| **Rate** | 5% | Stundensatz im Rahmen |

### Schwellenwerte

| Score | Aktion |
|-------|--------|
| ≥90% | 🔥 Hot Lead - sofort bewerben |
| 80-89% | ✅ Guter Match - bewerben |
| 70-79% | ⚠️ Okay - manuell prüfen |
| <70% | ❌ Skip - nicht bewerben |

---

## Teil 5: CRM-Integration

### Automatisch erstellte Issues

**Title:** `{Position} @ {Agentur}`

**Labels:**
- `status::neu`
- `rate::95-105` (basierend auf Ausschreibung)
- `tech::kubernetes`, `tech::python`, etc.
- `match::80-90` (basierend auf Score)

**Description:**
```markdown
### Meta
- **Agentur:** XY Consulting
- **Rate:** 100 €/h
- **Match:** 85%
- **Remote:** 100%

### Anforderungen
[Aus Ausschreibung extrahiert]

### Match-Analyse
✅ Kubernetes: 5+ Jahre
✅ Python: Expert
⚠️ Terraform: nur Basics
```

---

## Troubleshooting

### Problem: "No new projects found"

**Ursache:** Freelancermap hat nichts Neues, oder Filter zu streng.

**Fix:** Crawl-Parameter in `config/crawl.yaml` anpassen.

### Problem: "Gmail draft creation failed"

**Ursache:** OAuth Token abgelaufen.

**Fix:**
1. `config/google/credentials.json` prüfen
2. Token refreshen: `python scripts/refresh_oauth.py`

### Problem: "Match score seems wrong"

**Ursache:** Profil-PDF nicht lesbar oder LLM halluziniert.

**Fix:**
1. Profil-PDF als Text extrahieren und prüfen
2. Matching-Prompt in `config/prompts/match.txt` anpassen

---

## Referenzen

- **CRM Runbook:** [crm.md](crm.md)
- **Profile:** `attachments/` Ordner
- **Schedule:** https://gitlab.com/wolfram_laube/blauweiss_llc/projects/clarissa/-/pipeline_schedules/4125172

---

## Änderungshistorie

| Datum | Änderung | Autor |
|-------|----------|-------|
| 2026-02-04 | Initial version | Wolfram + Claude |
