# HANDOVER: GCP Stockholm Discovery & Migration Cleanup

**Datum:** 2026-02-03
**Chat-Name:** "GCP Nordic Realitätscheck"
**Nächster Chat:** "Tech Debt Offensive: GDrive, Docker, Terraform"

---

## 🎯 Was wir erreicht haben

### 1. GCP VM Lokalisierung
**Problem:** Dokumentation behauptete VM sei in `europe-west1-b` (Belgien)
**Realität:** VM `gitlab-runner-nordic` läuft bereits in `europe-north2-a` (Stockholm) - günstigste EU-Region!

```bash
# Echte Konfiguration (verifiziert via gcloud)
Name:   gitlab-runner-nordic
Zone:   europe-north2-a (Stockholm, Schweden)
Status: RUNNING
IP:     34.51.248.133
```

### 2. Config-Fixes durchgeführt

| Datei | Fix |
|-------|-----|
| `.gitlab/runner-fallback.yml` | `GCP_ZONE: "europe-north2-a"`, `GCP_INSTANCE: "gitlab-runner-nordic"` |
| `.gitlab/gcp-migration.yml` | Template auf korrekte Source-Werte aktualisiert |

### 3. Migration-Template behalten
Für künftige Migrationen (Australien? 🦘):
```yaml
OLD_ZONE: "europe-north2-a"           # Aktuell
OLD_VM_NAME: "gitlab-runner-nordic"   # Aktuell
NEW_ZONE: "TBD_TARGET_ZONE"           # Bei Bedarf setzen
NEW_VM_NAME: "TBD_TARGET_NAME"        # Bei Bedarf setzen
```

### Migrations-Phasen

| Phase | Trigger | Aktion | Runner |
|-------|---------|--------|--------|
| 1. backup | `MIGRATION_PHASE=backup` | Snapshot erstellen, Config sichern | Alter Runner (gcp-shell) |
| 2. create | `MIGRATION_PHASE=create` | Neue VM aus Snapshot erstellen | Alter Runner (gcp-shell) |
| 3. register | **MANUELL** | SSH → Runner registrieren | - |
| 4. switch | `MIGRATION_PHASE=switch` | Verifizieren dass neuer Runner läuft | Neuer Runner (nordic) |
| 5. cleanup | `MIGRATION_PHASE=cleanup` | Alte VM löschen (nach 48h) | Neuer Runner (nordic) |

**Workflow:**
```bash
# Phase 1 & 2 (automatisch)
Pipeline triggern mit MIGRATION_PHASE=backup
Pipeline triggern mit MIGRATION_PHASE=create

# Phase 3 (manuell)
gcloud compute ssh NEW_VM_NAME --zone=NEW_ZONE
sudo gitlab-runner register ...

# Phase 4 & 5 (automatisch)
Pipeline triggern mit MIGRATION_PHASE=switch
# 48h warten...
Pipeline triggern mit MIGRATION_PHASE=cleanup
```

### 4. GitLab Free-Tier Epic Workaround
Pattern etabliert: `[EPIC]` als Title-Prefix + Related Issue Links
- Epic #13 mit 7 Child-Issues (#4-#10)
- Alle geschlossen mit Dokumentation

---

## 🔴 Offene Tech Debt (für nächsten Chat)

Pipeline #2303400961 zeigt 8 fehlgeschlagene Jobs:

| Job | Kategorie | Priorität |
|-----|-----------|-----------|
| `gdrive:sync-notebooks` | Integration | Medium |
| `gdrive:sync-credentials` | Integration | Medium |
| `docker-build` | Build | Low |
| `docker-test` | Build | Low |
| `terraform:validate` | IaC | Medium |
| `terraform:fmt` | IaC | Low |
| `terraform:plan` | IaC | Medium |
| `migration:backup` | ~~Migration~~ | ✅ Irrelevant |

---

## 📊 Aktuelle Infrastruktur

```
┌─────────────────────────────────────────────────────┐
│  gitlab-runner-nordic @ europe-north2-a (Stockholm) │
│  Status: RUNNING | Type: e2-micro | Kosten: Optimal │
└─────────────────────────────────────────────────────┘
         │
         ├── Tags: shell, gcp, gcp-shell, nordic, any-runner
         ├── Runner-Fallback: ✅ Korrekt konfiguriert
         └── Migration-Template: ✅ Bereit für Australien
```

---

## 🔗 Relevante Links

- **backoffice Repo:** https://gitlab.com/wolfram_laube/blauweiss_llc/ops/backoffice
- **Pipeline:** https://gitlab.com/wolfram_laube/blauweiss_llc/ops/backoffice/-/pipelines/2303400961
- **Geschlossene Issues:** #4-#10, #13 (Migration)
- **Früherer Transcript:** /mnt/transcripts/2026-02-03-14-25-06-gcp-runner-bandit-optimization.txt

---

## 💡 Ideen für später

1. **Multi-Armed Bandit Runner Selection** (aus früherem Chat)
   - Intelligente Runner-Auswahl basierend auf Verfügbarkeit & Performance
   - UCB1/Thompson Sampling für Exploration/Exploitation

2. **Lokale Runner registrieren**
   - mac#1, mac#2, yoga mit Tag `local-shell`
   - Würde GCP-Kosten weiter reduzieren

---

## 📝 Notizen

- Stockholm (europe-north2) ist günstiger als Finnland (europe-north1)
- Free-Tier e2-micro nur in US-Regionen (us-central1, us-west1, us-east1)
- VM hat "precarious employment situation" wegen Spot - Visum für Australien fraglich 🦘
