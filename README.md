# 🪓 Freelancer Admin - Viking Edition

Modulares Admin-Tool für Freelancer: Bewerbungen, Rechnungen, Timesheets, Controlling, Steuern.

> *"41% German precision, 34% Slavic improvisation, 20% Viking courage, 5% English politeness"*

## 🚀 Quick Start

```bash
# Klonen
git clone git@gitlab.com:wolfram_laube/blauweiss_llc/freelancer-admin.git
cd freelancer-admin

# Dependencies
pip install -r requirements.txt

# Unified CLI
python cli.py applications list
python cli.py invoicing new --client "ACME" --hours 40
python cli.py timesheets log --project acme --hours 8 -d "Code review"
```

## 📁 Struktur

```
freelancer-admin/
│
├── modules/                    # Isolierte Tools
│   ├── applications/           # 📧 Bewerbungen & CV
│   ├── invoicing/              # 🧾 Rechnungen
│   ├── timesheets/             # ⏱️  Zeiterfassung
│   ├── controlling/            # 📊 Auswertungen
│   └── tax/                    # 🧮 Steuern
│
├── common/                     # Shared Code
│   ├── storage/                # S3/GDrive Abstraction
│   ├── auth/                   # Google OAuth etc.
│   ├── models/                 # Datenmodelle
│   └── templates/              # Shared Templates
│
├── config/                     # Credentials
│   ├── google/                 # OAuth & Service Account
│   ├── storage/                # S3/GCS/rclone
│   └── settings.yaml           # App Settings
│
├── attachments/                # CVs, Zertifikate
├── cli.py                      # Unified Entry Point
└── portal/                     # (Später) Web-UI
```

## 📦 Module

### 📧 Applications
Bewerbungen erstellen, Gmail Drafts, CV-Verwaltung.

```bash
python cli.py applications list
python cli.py applications send ibsc --mode draft
```

### 🧾 Invoicing
Rechnungen aus Typst-Templates generieren.

```bash
python cli.py invoicing new --client "nemensis AG" --hours 40
python cli.py invoicing list --year 2025
```

### ⏱️ Timesheets
Arbeitszeit erfassen und Reports erstellen.

```bash
python cli.py timesheets log --project nemensis --hours 8 -d "Architecture review"
python cli.py timesheets report --project nemensis --month 1
```

### 📊 Controlling
Finanzübersicht, Forecasts, Exporte für Steuerberater.

```bash
python cli.py controlling summary --year 2025
python cli.py controlling forecast --months 3
```

### 🧮 Tax
UVA, EÜR, Dokumentensammlung fürs Finanzamt.

```bash
python cli.py tax uva --year 2025 --quarter 4
python cli.py tax collect --year 2025
```

## 🔐 Credentials Setup

### Google OAuth (Gmail, GDrive)
```bash
# credentials.json liegt bereits in config/google/
# Beim ersten Aufruf öffnet sich der Browser für OAuth-Flow
```

### GCP Storage (S3-kompatibel)
```bash
# 1. GCP Console → Cloud Storage → Settings → Interoperability
# 2. HMAC Key erstellen
# 3. Speichern als config/storage/gcs-hmac.json
```

## 🐳 Docker

```bash
docker build -t freelancer-admin .
docker run -p 8000:8000 freelancer-admin

# Oder aus GitLab Registry:
docker pull registry.gitlab.com/wolfram_laube/blauweiss_llc/freelancer-admin:latest
```

## 🔄 CI/CD

Pipeline baut automatisch:
- Python Wheel
- Docker Image → GitLab Registry
- Binaries (bei Tags)

## 📜 Roadmap

- [x] v1.0 - Applications Module (Bewerbungen)
- [ ] v1.1 - Invoicing Migration (aus corporate/)
- [ ] v1.2 - Timesheets Implementation
- [ ] v1.3 - Controlling Basics
- [ ] v2.0 - Web Portal (FastAPI + React)
- [ ] v2.1 - Storage Integration (GCS/S3)
- [ ] v3.0 - Mobile App? 🤔

## 📄 Lizenz

Privat / Blauweiss LLC

---

*Built with ☕ and 🪓 by a Viking Freelancer*
