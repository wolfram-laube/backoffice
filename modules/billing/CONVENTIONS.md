# BLAUWEISS EDV LLC - Billing Conventions

> Per ADR-019: Billing Folder Structure for Contractors

## Overview

```
BLAUWEISS-EDV-LLC/
└── Buchhaltung/
    ├── clients/         # → Documents for customers (external)
    └── contractors/     # → Internal LLC records (private)
```

## Filename Conventions

### Client Documents (External)

These go to `Buchhaltung/clients/{client}/{year}/{month}/`

| Document | Filename Pattern | Example |
|----------|------------------|---------|
| Invoice | `{client}_{year}-{month}_invoice_AR_{nr}.pdf` | `nemensis_2026-01_invoice_AR_001.pdf` |
| Consolidated Timesheet | `{client}_{year}-{month}_timesheet.pdf` | `nemensis_2026-01_timesheet.pdf` |

### Contractor Documents (Internal)

These go to `Buchhaltung/contractors/{person}/{year}/{month}/{client}/`

| Document | Filename Pattern | Example |
|----------|------------------|---------|
| Individual Timesheet | `{person}_{client}_{year}-{month}_timesheet.pdf` | `wolfram_nemensis_2026-01_timesheet.pdf` |
| Honorar Note | `{person}_{client}_{year}-{month}_honorar.pdf` | `wolfram_nemensis_2026-01_honorar.pdf` |

## Document Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                        BLAUWEISS EDV LLC                            │
│                                                                     │
│   CONTRACTOR INPUT                    CLIENT OUTPUT                 │
│   ────────────────                    ─────────────                 │
│                                                                     │
│   wolfram_nemensis_2026-01_timesheet.pdf ──┐                       │
│   wolfram_nemensis_2026-01_honorar.pdf     │                       │
│                                            │                        │
│   ian_nemensis_2026-01_timesheet.pdf ──────┼─► consolidate         │
│   ian_nemensis_2026-01_honorar.pdf         │      │                │
│                                            │      ▼                │
│                                            │  nemensis_2026-01_timesheet.pdf
│                                            │         +              │
│                                            └─► nemensis_2026-01_invoice_AR_001.pdf
│                                                      │              │
└──────────────────────────────────────────────────────┼──────────────┘
                                                       ▼
                                                    KUNDE
```

## Known Identifiers

### Contractors
- `wolfram` - Wolfram Laube
- `ian` - Ian Matejka
- `mike` / `michal` - Michal Matejka

### Clients
- `nemensis` - Nemensis GmbH
- `elia` - Elia Group
- `50hertz` - 50Hertz

## CI/CD Integration

### Manual Trigger (Pages)

Visit: https://wolfram-laube.gitlab.io/blauweiss-llc/clarissa/billing-trigger.html

Or via curl:
```bash
curl -X POST \
  -F "token=glptt-4oo419PQs1AxzGJoNnx1" \
  -F "ref=main" \
  -F "variables[FORCE_BILLING]=true" \
  "https://gitlab.com/api/v4/projects/77260390/trigger/pipeline"
```

### Pipeline Jobs

| Job | Description | Output |
|-----|-------------|--------|
| `build_invoice` | Compile Typst → PDF | `billing/output/*.pdf` |
| `upload_invoice` | Upload to GDrive | Buchhaltung folders |
| `billing_email` | Create Gmail draft | Draft in Wolfram's inbox |

## Adding a New Contractor

1. Add name to `KNOWN_CONTRACTORS` in `billing/scripts/upload_to_drive.py`
2. Create their timesheet template in `billing/templates/`
3. Create folder: `Buchhaltung/contractors/{name}/`

## Adding a New Client

1. Add name to `KNOWN_CLIENTS` in `billing/scripts/upload_to_drive.py`
2. Create invoice template in `billing/templates/`
3. Folders auto-created on first upload

## Legacy Filename Support

The upload script auto-detects and converts legacy formats:

| Legacy | Converted To |
|--------|--------------|
| `AR_001_2026_nemensis.pdf` | `nemensis_2026-01_invoice_AR_001.pdf` |
| `2026-01_timesheet_nemensis_de.pdf` | `nemensis_2026-01_timesheet.pdf` |
| `2026-01_timesheet_nemensis_wolfram_de.pdf` | `wolfram_nemensis_2026-01_timesheet.pdf` |

⚠️ Warning shown when legacy formats detected. Please rename files to new convention.
