# 📎 Attachments

Dieser Ordner enthält die CVs und Zertifikate für Bewerbungen.

## ⚠️ WICHTIG: Nicht im Git!

Die Dateien in diesem Ordner werden durch `.gitignore` vom Repository ausgeschlossen.
Das ist Absicht - persönliche Dokumente sollten nicht in Git sein.

## 📋 Benötigte Dateien

Kopiere folgende Dateien aus `bewerbung-tool-private.zip` hierher:

### Wolfram Laube (Standard)
```
Profil_Laube_w_Summary_DE.pdf    ← Hauptprofil Deutsch
Profil_Laube_w_Summary_EN.pdf    ← Hauptprofil Englisch
Studienerfolg_08900915_1.pdf     ← JKU Studienbestätigung
```

### Ian Matejka (Team)
```
CV_Ian_Matejka_DE.pdf            ← CV Deutsch
IanMatejkaCV1013MCM.pdf          ← CV Englisch
```

### Michael Matejka (Team)
```
CV_Michael_Matejka_DE.pdf        ← CV Deutsch
Michael_Matejka_CV_102025.pdf    ← CV Englisch
```

## 🔧 Setup

```bash
# Nach dem Klonen des Repos:
cd bewerbung-tool

# Private-ZIP entpacken (z.B. aus Claude Download)
unzip ~/Downloads/bewerbung-tool-private.zip

# Dateien kopieren
cp private-files/attachments/* attachments/
cp private-files/credentials.json config/

# Verifizieren (sollten alle als "ignored" erscheinen)
git status
```

## 📝 Hinweis

Die `.gitignore` enthält sowohl die spezifischen Dateinamen als auch 
generische Pattern (`*.pdf`, `*.docx`) als Backup-Schutz.

Neue CVs hier ablegen → automatisch ignoriert! ✅
