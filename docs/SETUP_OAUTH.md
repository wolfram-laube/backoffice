# Google OAuth Setup

## Voraussetzungen

- Google Account
- Python 3.8+

## Schritt 1: Google Cloud Projekt

1. Öffne: https://console.cloud.google.com
2. Oben links → "Select a project" → "New Project"
3. Name: `bewerbung-tool` (oder bestehendes Projekt nutzen)
4. Create

## Schritt 2: Gmail API aktivieren

1. Linkes Menü → "APIs & Services" → "Library" (Bibliothek)
2. Suche: "Gmail API"
3. Klick auf "Gmail API" → "Enable" (Aktivieren)

## Schritt 3: OAuth Consent Screen

1. Linkes Menü → "APIs & Services" → "OAuth consent screen" (OAuth-Zustimmungsbildschirm)
2. User Type: "External" → Create
3. Ausfüllen:
   - App name: `Bewerbung Tool`
   - User support email: Deine E-Mail
   - Developer contact: Deine E-Mail
4. Save and Continue (alle weiteren Screens durchklicken)
5. Bei "Test users" → Add Users → Deine Gmail-Adresse hinzufügen

## Schritt 4: Credentials erstellen

1. Linkes Menü → "APIs & Services" → "Credentials" (Anmeldedaten)
2. "+ Create Credentials" → "OAuth client ID"
3. Application type: **Desktop app**
4. Name: `Bewerbung CLI`
5. Create
6. **"Download JSON"** klicken!
7. Datei speichern als: `config/credentials.json`

## Schritt 5: Erster Start

```bash
cd bewerbung-tool
python src/bewerbung.py
```

Beim ersten Mal:
1. Browser öffnet sich automatisch
2. Mit Google-Account einloggen
3. "Diese App wurde nicht verifiziert" → **Erweitert** → **Trotzdem fortfahren**
4. **Zulassen** klicken
5. ✅ Token wird in `config/token.pickle` gespeichert

## Troubleshooting

### "credentials.json nicht gefunden"
→ Datei muss in `config/credentials.json` liegen

### "Token expired"
→ `config/token.pickle` löschen und neu starten

### "Access blocked: This app's request is invalid"
→ OAuth Consent Screen prüfen, Test User hinzufügen

### "Error 403: access_denied"
→ Gmail API aktiviert? Test User hinzugefügt?
