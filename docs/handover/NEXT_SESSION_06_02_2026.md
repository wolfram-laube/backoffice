# Nächste Session: MAB Deploy + CI Integration

## Kontext

MAB Runner-Auswahl komplett implementiert (v0.3.1), aber noch **nicht deployed**.
Code ist auf `main`, Cloud Run läuft noch v0.1.0.

## Erledigt (Session 06.02.2026)

- ✅ GCS State Persistence (`gs://blauweiss-mab-state`)
- ✅ 6 Runner als Arms (4 Docker + 2 K8s)
- ✅ Webhooks auf 3 Repos (Backoffice, Portal, CLARISSA)
- ✅ `.mab-enabled` CI Template + `mab:recommend` / `mab:stats` Jobs
- ✅ Availability-Check via GitLab API (`/availability`)
- ✅ GCP Auto-Start wenn alle Runner offline (`/vm/start`)
- ✅ GCP Auto-Stop nach 5 Min Idle (nur wenn MAB gestartet hat)
- ✅ Handover: `docs/handover/HANDOVER_MAB_FULL_06_02_2026.md`

## Offen (Prio-Reihenfolge)

1. **Cloud Run Deploy** — `cloud-run:build` + `cloud-run:deploy` durchbringen
   - Mehrere Pipelines getriggert, Jobs stehen auf `created`
   - Nach Deploy: `curl .../` sollte v0.3.1 + 6 Runner + GCS zeigen
2. **`.mab-enabled` auf Key-Jobs** — billing, tests, pages erweitern
3. **Parent-Child Pipeline** — echte dynamische Tag-Selektion
4. **MAB Dashboard** im Portal (Stats-Seite)
5. **NSAI Epic #27** — Symbolische Constraints (Future Work)

## Repos

- Backoffice: `blauweiss_llc/ops/backoffice` (77555895)
- Portal: `blauweiss_llc/portal` (78288201)
- CLARISSA: `blauweiss_llc/projects/clarissa` (77260390)

## Zugang

- GitLab Token: `glpat--wmS4xEWjjWdOgaOd7oDWG86MQp1OnN4Y3gK.01.101dpjjbj`
- GCP Projekt: `myk8sproject-207017`
- MAB Service: https://runner-bandit-m5cziijwqa-lz.a.run.app/

## Handover lesen

```bash
curl -sf --header "PRIVATE-TOKEN: glpat--wmS4xEWjjWdOgaOd7oDWG86MQp1OnN4Y3gK.01.101dpjjbj" \
  "https://gitlab.com/api/v4/projects/77555895/repository/files/docs%2Fhandover%2FHANDOVER_MAB_FULL_06_02_2026.md/raw?ref=main"
```
