# GitLab Runner Setup

## Übersicht

Das Projekt nutzt zwei GitLab Runner für CI/CD:

| Runner | Plattform | Tags | Wann aktiv |
|--------|-----------|------|------------|
| 🍎 `mac-shell` | macOS (lokal) | `shell, macos, local` | Bei Login |
| ☁️ `gcp-shell` | GCP VM (e2-small) | `shell, gcp, linux` | 24/7 oder on-demand |

## Schnellstart

### Status prüfen
```bash
./scripts/runner-flip.sh status
```

### Manuell umschalten
```bash
./scripts/runner-flip.sh mac    # Mac an, GCP aus (spart ~$13/Mo)
./scripts/runner-flip.sh gcp    # GCP an, Mac aus (spart Ressourcen)
./scripts/runner-flip.sh auto   # Mac bevorzugt, GCP als Fallback
```

### Automatisches Flip-Flop installieren
```bash
./scripts/runner-setup-auto.sh install
```

Nach der Installation:
- **Mac Login** → Mac Runner startet, GCP stoppt
- **Mac Sleep** → GCP startet, Mac stoppt  
- **Mac Wake** → Mac startet, GCP stoppt

## Detaillierte Anleitung

### Mac Runner einrichten

```bash
# 1. GitLab Runner installieren
brew install gitlab-runner

# 2. Runner registrieren
./scripts/setup-runner.sh
# Oder mit Token direkt:
./scripts/setup-runner.sh $(cat config/gitlab/runner-mac.token)

# 3. Als Service starten
brew services start gitlab-runner
```

### GCP Runner einrichten

```bash
# 1. gcloud CLI authentifizieren
gcloud auth login

# 2. VM erstellen und Runner registrieren
./scripts/setup-gcp-runner.sh $(cat config/gitlab/runner-gcp.token) myk8sproject-207017

# 3. Manuell verbinden (falls nötig)
gcloud compute ssh gitlab-runner --zone=europe-west3-a
```

### GCP Runner manuell verwalten

```bash
# VM starten
gcloud compute instances start gitlab-runner --zone=europe-west3-a

# VM stoppen (spart Geld!)
gcloud compute instances stop gitlab-runner --zone=europe-west3-a

# SSH Zugang
gcloud compute ssh gitlab-runner --zone=europe-west3-a

# Runner Status auf VM prüfen
gcloud compute ssh gitlab-runner --zone=europe-west3-a --command="sudo gitlab-runner list"
```

## Kosten

| Zustand | Kosten/Monat |
|---------|--------------|
| GCP VM läuft (e2-small) | ~$13 |
| GCP VM gestoppt | ~$0.80 (nur Disk) |
| Mac Runner | $0 (eigene Hardware) |

**Empfehlung:** Mac als Default, GCP nur bei Bedarf starten.

## Tokens

Die Runner-Tokens sind im Repo gespeichert:

```
config/gitlab/
├── runner-mac.token   # Mac Runner
├── runner-gcp.token   # GCP Runner
├── pat.token          # Personal Access Token (API)
└── README.md
```

### Token erneuern

Falls ein Token kompromittiert ist:
1. GitLab → Settings → CI/CD → Runners
2. Runner bearbeiten → "Reset token"
3. Neues Token in entsprechende Datei speichern
4. Runner neu registrieren

## Troubleshooting

### Runner offline?
```bash
# Mac
brew services restart gitlab-runner
gitlab-runner status

# GCP
gcloud compute ssh gitlab-runner --zone=europe-west3-a --command="sudo gitlab-runner restart"
```

### Pipeline hängt?
```bash
# Prüfen welcher Runner Jobs hat
./scripts/runner-flip.sh status

# In GitLab: CI/CD → Pipelines → Job → Runner Info
```

### GCP VM antwortet nicht?
```bash
# VM neu starten
gcloud compute instances reset gitlab-runner --zone=europe-west3-a
```

## Dateien

```
scripts/
├── setup-runner.sh        # Mac Runner Setup
├── setup-gcp-runner.sh    # GCP Runner Setup
├── runner-flip.sh         # Manuelles Umschalten
└── runner-setup-auto.sh   # Automatisches Flip-Flop
```

## Architektur

```
┌─────────────────────────────────────────────────────────────┐
│                        GitLab                               │
│                    (gitlab.com)                             │
└─────────────────────┬───────────────────────────────────────┘
                      │
        ┌─────────────┴─────────────┐
        │                           │
        ▼                           ▼
┌───────────────┐           ┌───────────────┐
│  🍎 Mac       │           │  ☁️ GCP       │
│  mac-shell    │           │  gcp-shell    │
│               │           │               │
│  • Kostenlos  │           │  • ~$13/Mo    │
│  • Bei Login  │           │  • 24/7       │
│  • Lokal      │           │  • Remote     │
└───────────────┘           └───────────────┘
        │                           │
        └─────────────┬─────────────┘
                      │
                      ▼
              Flip-Flop Script
              (automatisch oder manuell)
```
