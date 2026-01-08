# Bewerbungs-Tool

Automatisiertes Tool für Freelance-Bewerbungen mit Gmail-Draft-Erstellung und freelancermap-Integration.

## Features

- 📧 **Gmail Draft erstellen** mit Attachments (OAuth)
- 🌐 **Browser öffnen** für schnelle Bewerbungen
- 📋 **Text kopieren** für freelancermap-Formulare
- 👥 **Team-Support** (Wolfram, Ian, Michael CVs)

## Quick Start

```bash
# 1. Repository klonen
git clone git@gitlab.com:blauweiss/bewerbung-tool.git
cd bewerbung-tool

# 2. Virtual Environment (empfohlen)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# oder: venv\Scripts\activate  # Windows

# 3. Dependencies installieren
pip install -r requirements.txt

# 4. Credentials einrichten (siehe docs/SETUP_OAUTH.md)
cp config/credentials.json.example config/credentials.json
# Dann credentials.json mit deinen Google OAuth Daten füllen

# 5. CVs in attachments/ legen
# (nicht im Repo, siehe .gitignore)

# 6. Starten
python src/bewerbung.py
```

## Projektstruktur

```
bewerbung-tool/
├── src/
│   ├── bewerbung.py          # Hauptprogramm
│   ├── gmail_client.py       # Gmail API Wrapper
│   ├── templates.py          # Bewerbungstexte
│   └── config.py             # Konfiguration
│
├── config/
│   ├── credentials.json      # Google OAuth (NICHT im Git!)
│   ├── credentials.json.example
│   └── settings.yaml         # Einstellungen (Rate, Kontakt, etc.)
│
├── attachments/              # CVs und Zertifikate (NICHT im Git!)
│   ├── .gitkeep
│   └── README.md
│
├── templates/
│   ├── bewerbungen.yaml      # Bewerbungstexte als YAML
│   └── html/
│       ├── gmail_compose.html
│       └── freelancermap.html
│
├── docs/
│   ├── SETUP_OAUTH.md        # Google OAuth Anleitung
│   └── USAGE.md              # Benutzung
│
├── tests/
│   └── test_gmail_client.py
│
├── .gitignore
├── .gitlab-ci.yml            # CI/CD (optional)
├── requirements.txt
├── pyproject.toml            # Modern Python packaging
└── README.md
```

## Konfiguration

### settings.yaml

```yaml
bewerber:
  name: "Wolfram Laube"
  telefon: "+43 664 4011521"
  email: "wolfram.laube@blauweiss-edv.at"
  stundensatz: 105

attachments:
  standard:
    - "Profil_Laube_w_Summary_DE.pdf"
    - "Studienerfolg_08900915_1.pdf"
  optional:
    - "Profil_Laube_w_Summary_EN.pdf"
    - "CV_Ian_Matejka_DE.pdf"
    - "CV_Michael_Matejka_DE.pdf"
```

## Roadmap

- [x] v1.0 - CLI Tool
- [x] v1.1 - GitLab CI/CD + Docker
- [ ] v2.0 - Web UI (FastAPI)
- [ ] v2.1 - GCP Cloud Run Deployment
- [ ] v3.0 - Integration mit freelancermap-Scraper

## Docker

```bash
# Image aus GitLab Registry ziehen
docker pull registry.gitlab.com/blauweiss/bewerbung-tool:latest

# Lokal bauen
docker build -t bewerbung-tool .

# Web-Server starten (Port 8000)
docker run -p 8000:8000 bewerbung-tool

# CLI im Container
docker run bewerbung-tool python src/bewerbung.py --list
```

**GitLab Registry:** Nach jedem Push auf `main` wird automatisch ein neues Image gebaut:
```
registry.gitlab.com/blauweiss/bewerbung-tool:latest
registry.gitlab.com/blauweiss/bewerbung-tool:<commit-sha>
registry.gitlab.com/blauweiss/bewerbung-tool:<tag>  # bei Git Tags
```

## Lizenz

Privat / Blauweiss EDV e.U.
