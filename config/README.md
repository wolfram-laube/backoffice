# ⚙️ Konfiguration

## 📁 Dateien in diesem Ordner

| Datei | Im Git? | Beschreibung |
|-------|---------|--------------|
| `settings.yaml` | ✅ Ja | Allgemeine Einstellungen (Rate, Signatur, etc.) |
| `credentials.json.example` | ✅ Ja | Template für Google OAuth |
| `credentials.json` | ❌ Nein | **Deine** Google OAuth Credentials |
| `token.pickle` | ❌ Nein | Gespeicherter Auth-Token (automatisch erstellt) |

## 🔐 Setup: credentials.json

### Option A: Aus Private-ZIP

```bash
cp private-files/credentials.json config/
```

### Option B: Selbst erstellen

Siehe `docs/SETUP_OAUTH.md` für die komplette Anleitung.

Kurzversion:
1. https://console.cloud.google.com → Gmail API aktivieren
2. OAuth Credentials erstellen (Desktop App)
3. JSON herunterladen → hier als `credentials.json` speichern

## ⚠️ Sicherheit

- `credentials.json` enthält deinen Google API Client Secret
- `token.pickle` enthält deinen Auth-Token
- **NIEMALS** diese Dateien committen oder teilen!
- Sie sind in `.gitignore` gelistet als Schutz
