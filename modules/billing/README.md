# 💰 CLARISSA Billing System (Typst)

Generate professional invoices and timesheets with bidirectional GitLab sync.

## 🔄 Complete Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│    GitLab (/spend)  ◄────────────────►  Timesheet.typ      │
│         │                    ▲                │             │
│         │                    │                │             │
│         ▼                    │                ▼             │
│    [generate_timesheet.py]   │   [Manual Edits]            │
│         │                    │                │             │
│         ▼                    │                │             │
│    timesheet.typ ────────────┘                │             │
│         │                                     │             │
│         │      [sync_timesheet.py] ◄──────────┘             │
│         │                                                   │
│         ▼                                                   │
│    [generate_invoice.py --from-timesheet]                  │
│         │                                                   │
│         ▼                                                   │
│    invoice.pdf + timesheet.pdf                             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Step 1: Track Time in GitLab

```bash
# In any issue comment:
/spend 4h           # Log 4 hours today
/spend 2h 2026-01-15  # Log 2 hours on specific date
```

### Step 2: Generate Timesheet

```bash
export GITLAB_TOKEN="glpat-xxx"

python billing/scripts/generate_timesheet.py \
    --client nemensis \
    --period 2026-01 \
    --lang de
```

Output:
- `billing/output/2026-01_timesheet_nemensis_de.typ` (editable)
- `billing/output/2026-01_timesheet_nemensis_de.pdf`
- `billing/output/2026-01_timesheet_nemensis_de.sync.json` (for sync)

### Step 3: Review & Edit (if needed)

```bash
# Edit the timesheet to add forgotten entries
vim billing/output/2026-01_timesheet_nemensis_de.typ

# Change:
#   "15": (4, "Meeting"),
# To:
#   "15": (6, "Meeting + Documentation"),
```

### Step 4: Sync Changes Back to GitLab

```bash
python billing/scripts/sync_timesheet.py \
    billing/output/2026-01_timesheet_nemensis_de.typ
```

This creates/updates a "⏱️ Timesheet Corrections" issue with `/spend` entries.

### Step 5: Generate Invoice

```bash
python billing/scripts/generate_invoice.py \
    --from-timesheet billing/output/2026-01_timesheet_nemensis_de.typ
```

Output:
- `billing/output/AR_001_2026_nemensis.typ`
- `billing/output/AR_001_2026_nemensis.pdf`
- Timesheet PDF also compiled as attachment

## 📁 Directory Structure

```
billing/
├── config/
│   ├── clients.yaml      # Client definitions
│   └── sequences.yaml    # Invoice numbering
├── templates/
│   ├── invoice-en-us.typ # US customers
│   ├── invoice-en-eu.typ # EU customers (reverse charge)
│   ├── rechnung-de.typ   # German customers
│   ├── timesheet.typ     # Timesheet template (i18n)
│   └── logo.jpg
├── scripts/
│   ├── generate_timesheet.py  # GitLab → Timesheet
│   ├── sync_timesheet.py      # Timesheet → GitLab
│   └── generate_invoice.py    # Timesheet → Invoice
├── output/
│   ├── 2026-01_timesheet_nemensis_de.typ
│   ├── 2026-01_timesheet_nemensis_de.pdf
│   ├── 2026-01_timesheet_nemensis_de.sync.json
│   ├── AR_001_2026_nemensis.typ
│   └── AR_001_2026_nemensis.pdf
└── README.md
```

## 🌍 Languages

Timesheets support 5 languages:

| Code | Language | Example |
|------|----------|---------|
| `en` | English | Timesheet / Service Report |
| `de` | Deutsch | Leistungsschein / Timesheet |
| `vi` | Tiếng Việt | Bảng Chấm Công |
| `ar` | العربية | كشف الحضور |
| `is` | Íslenska | Tímaskýrsla |

```bash
python billing/scripts/generate_timesheet.py -c nemensis -p 2026-01 --lang vi
```

## 📋 Invoice Templates

| Template | Use Case | Currency | VAT |
|----------|----------|----------|-----|
| `invoice-en-us.typ` | US customers | USD | None |
| `invoice-en-eu.typ` | EU customers | EUR | Reverse Charge |
| `rechnung-de.typ` | DE/AT customers | EUR | Reverse Charge |

## 🔢 Invoice Numbering

Format: `AR_{sequence}_{year}`

Examples: `AR_001_2026`, `AR_015_2026`

Global sequence across all clients, tracked in `config/sequences.yaml`.

## ⚙️ Configuration

### Adding a Client

Edit `billing/config/clients.yaml`:

```yaml
clients:
  newclient:
    name: "New Client GmbH"
    short: "NC"
    template: "rechnung-de"  # or invoice-en-us, invoice-en-eu
    currency: "EUR"
    address:
      line1: "Hauptstraße 1"
      city: "D - 10115 Berlin"
      country: ""
    registration_id: "HRB 12345 Berlin"
    vat_id: "DE123456789"
    contract_number: "00003154"
    rates:
      remote: 105
      onsite: 120
```

## 🛠️ Command Reference

### generate_timesheet.py

```bash
# Basic usage
python generate_timesheet.py --client CLIENT --period YYYY-MM

# Options
  --client, -c    Client ID (required)
  --period, -p    Period YYYY-MM (required)
  --lang, -l      Language: en, de, vi, ar, is (default: de)
  --no-pdf        Generate .typ only
  --dry-run       Show what would be fetched
```

### sync_timesheet.py

```bash
# Basic usage
python sync_timesheet.py TIMESHEET.typ

# Options
  --dry-run       Show changes without syncing
  --force         Sync even if no changes
```

### generate_invoice.py

```bash
# From timesheet (recommended)
python generate_invoice.py --from-timesheet TIMESHEET.typ

# Direct (legacy)
python generate_invoice.py --client CLIENT --hours 184
python generate_invoice.py --client CLIENT --period 2026-01

# Options
  --from-timesheet, -t    Generate from timesheet file
  --client, -c            Client ID
  --period, -p            Fetch from GitLab for period
  --hours                 Manual hours entry
  --remote/--onsite       Type of hours
  --date                  Invoice date YYYY-MM-DD
  --no-pdf                Generate .typ only
  --dry-run               Preview only
```

## 📅 Holiday Support

Timesheets automatically mark:

- 🔴 **Weekends** (Saturday, Sunday)
- 🟡 **Holidays** (DE and AT)

Including Easter-based holidays:
- Karfreitag (DE only)
- Ostermontag
- Christi Himmelfahrt
- Pfingstmontag
- Fronleichnam

## 🔧 Requirements

```bash
# Typst
curl -fsSL https://typst.community/typst-install/install.sh | sh

# Python
pip install pyyaml requests

# Environment
export GITLAB_TOKEN="glpat-xxx"
export GITLAB_PROJECT_ID="77260390"
```

## 🎨 Customization

### Colors

Edit the color definitions in `timesheet.typ`:

```typst
let weekend_color = rgb("#ff6b6b")   // Bold red
let holiday_color = rgb("#ffd93d")    // Bold yellow
let header_color = rgb("#00aeef")     // BlauWeiss blue
```

### Font

All templates use **Poppins** for a modern look. Change in templates:

```typst
set text(font: "Poppins", size: 10pt)
```
