# Blauweiss Operations

**Zentrale Steuerung für Freelance Business Operations**

---

<div class="grid cards" markdown>

-   :material-view-dashboard:{ .lg .middle } **Operations Portal**

    ---

    Live Dashboard mit Pipeline-Triggern und Status-Übersicht

    [:octicons-arrow-right-24: Portal öffnen](portal.html)

-   :material-account-group:{ .lg .middle } **CRM System**

    ---

    Bewerbungen als GitLab Issues mit Kanban Board

    [:octicons-arrow-right-24: CRM Board](https://gitlab.com/wolfram_laube/blauweiss_llc/ops/crm/-/boards/10081703)

-   :material-rocket-launch:{ .lg .middle } **Quick Start**

    ---

    Tägliche Workflows und Pipeline-Trigger

    [:octicons-arrow-right-24: Los geht's](ops/quickstart.md)

-   :material-api:{ .lg .middle } **API Reference**

    ---

    GitLab API Endpoints und Automation Scripts

    [:octicons-arrow-right-24: API Docs](ops/api-reference.md)

</div>

---

## Quick Actions

| Action | Trigger | Schedule |
|--------|---------|----------|
| 🔍 Applications Crawl | [Manual](triggers/applications-crawl.html) | Mo-Fr 08:00 |
| ✉️ Draft Generator | [Manual](triggers/drafts.html) | On Demand |
| 🔍 Match Finder | [Manual](triggers/match.html) | On Demand |
| ✅ CRM Integrity Check | [Manual](triggers/crm-integrity.html) | Mo 07:00 |
| 💰 Monthly Billing | [Manual](billing-trigger.html) | 1. des Monats |

---

## Repository Structure

```
blauweiss_llc/
├── ops/
│   ├── backoffice/   ← Du bist hier (Portal, CI, Code)
│   ├── crm/          ← Bewerbungs-Issues & Board
│   ├── MAGNUS/       ← Akquise-Templates
│   └── corporate/    ← Legal, Branding
└── projects/
    └── CLARISSA/     ← Research (Reservoir Simulation)
```

---

## Documentation

- [📚 Handover Documents](handover/HANDOVER_CI_REFACTOR_03_02_2026.md) — Session Notes & Übergaben
- [🚀 Quick Start](ops/quickstart.md) — Tägliche Workflows
- [📊 CRM Guide](ops/crm.md) — Issue-basiertes Tracking
