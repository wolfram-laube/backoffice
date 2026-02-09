# HANDOVER: AppTrack Sprint 5 — Application Portal & Draft Engine

**Datum:** 2026-02-09
**MR:** !22 — `feature/56-apptrack-sprint5-portal → main`

---

## 🎯 Scope

End-to-End Application Management im Dashboard Portal.

**Vorher:** Dashboard zeigt Tabelle + Charts. Aktion auf Bewerbungen nur außerhalb des Portals möglich.
**Nachher:** Klick auf Bewerbung → Detail-Panel mit Draft-Editor, Status-Workflow, Kommunikations-Log und Gmail-Integration.

---

## ✅ Deliverables

| Feature | Status |
|---|---|
| Detail-Panel (Slide-Over) | ✅ |
| Match-Breakdown + Projekt-Details | ✅ |
| Draft-Editor (3 Profile: Standard, AI, Team) | ✅ |
| Attachment-Picker (CV DE/EN, JKU Zertifikat) | ✅ |
| Status-Workflow (8 Status-Buttons) | ✅ |
| Kommunikations-Log + Bewertung (1-5 ⭐) | ✅ |
| "→ Gmail Draft" Button → CI Pipeline | ✅ |
| CI Job: `apptrack:create-draft` | ✅ |
| CI Script: `apptrack_create_single_draft.py` | ✅ |

---

## 📐 User Flow

```
1. Bewerbungen-Tab oder Vorhölle-Tab
     ↓ Klick auf Zeile / Card-Titel
2. Detail-Panel gleitet von rechts rein
     ├── Header: Titel, Score, Badges, Meta-Grid, Keywords
     ├── Tab "✉️ Anschreiben":
     │     ├── Profil-Auswahl (Standard / AI / Team)
     │     ├── Empfänger-Email Feld
     │     ├── Betreff (auto-generiert)
     │     ├── Textarea mit generiertem Anschreiben (editierbar)
     │     ├── Attachment-Checkboxen (CV DE ✓, CV EN, JKU Cert)
     │     └── Buttons: [📧 → Gmail Draft] [📋 Kopieren] [🔄 Neu]
     ├── Tab "📊 Status":
     │     ├── 8 Status-Buttons (versendet → vertrag/absage)
     │     └── History (auto-logged)
     └── Tab "💬 Kommunikation":
           ├── Freitext-Notiz + Bewertung (1-5 ⭐)
           └── Chronologischer Log aller Einträge
```

---

## 📧 Gmail Draft Flow

```
Portal: "→ Gmail Draft" Button
  → Prompt: GitLab PAT eingeben
    → POST /api/v4/projects/{id}/pipeline
        variables: APPTRACK_SINGLE_DRAFT=true, DRAFT_DATA_B64=<base64>
          → CI Job: apptrack:create-draft
            → apptrack_create_single_draft.py
              → Decode DRAFT_DATA_B64
              → Download Attachments (Corporate Repo / Project Files)
              → Gmail API: Create Draft with Attachments
              → Output: apptrack_draft_results.json
```

---

## 🧠 Draft Profile Templates

| Profil | Trigger | Focus |
|---|---|---|
| **Standard** | Default | Cloud/DevOps, CKA/CKAD, 50Hertz |
| **AI Focus** | AI keywords in title OR manual select | AI Bachelor, LLM/RAG, Python ML |
| **Team** | Manual select | Wolfram + Ian Matejka |

Auto-Detection: Wenn Titel AI/ML/LLM/KI enthält oder match_reasons.is_ai=true → AI-Profil wird automatisch gewählt.

---

## 📁 Files Changed

| File | Change |
|---|---|
| `docs/apptrack-dashboard.html` | +650 lines: detail panel, draft editor, status workflow, comm log |
| `scripts/ci/apptrack_create_single_draft.py` | NEW: Gmail draft with attachments |
| `.gitlab/applications.yml` | NEW job: `apptrack:create-draft` |

---

## ⚠️ Known Limitations

1. **Communication Log ist client-side** — Daten gehen bei Page Reload verloren. Persistence via dashboard.json Export oder LocalStorage ist Sprint 6 Material.
2. **Status-Changes sind client-side** — CRM Sync via Pipeline ist vorhanden (bestehender `crm_update_on_draft.py`) aber noch nicht aus dem Detail-Panel getriggert.
3. **Gmail Token** wird per Prompt abgefragt — könnte in Settings persistent gespeichert werden.
4. **Attachment-Download** aus Corporate Repo benötigt GITLAB_API_TOKEN in CI Variables.
