# Teststrategie — ops/backoffice

## Prinzip

> **Ein Use Case, getestet auf jeder Ebene der Pyramide.**

Tests sind **Use-Case-modular**: Jeder Business-Workflow (z.B. "Bewerbung erstellen") wird
als zusammenhängender Use Case betrachtet und auf allen drei Ebenen getestet — mit
denselben Fixture-Daten. Das garantiert **Kohärenz** zwischen den Ebenen und
**flächendeckende** Abdeckung ohne Redundanz.

---

## Testpyramide

```
                    ╱╲
                   ╱  ╲
                  ╱ E2E╲         roundtrip-test.yml
                 ╱──────╲        Reale APIs, Gmail, CRM
                ╱        ╲       Wöchentlich / manuell
               ╱──────────╲
              ╱ Integration ╲    tests/integration/
             ╱   (Mocked)    ╲   Modul-übergreifend, Mock-APIs
            ╱─────────────────╲  Bei MR + Push
           ╱                   ╲
          ╱     Unit Tests      ╲  tests/unit/
         ╱   (Isoliert, schnell) ╲ Einzelne Funktionen
        ╱─────────────────────────╲ Bei MR + Push
```

| Ebene | Scope | I/O | Trigger | Laufzeit |
|-------|-------|-----|---------|----------|
| **Unit** | Einzelne Funktion | Kein I/O | Push, MR | < 1s |
| **Integration** | Modul-übergreifend | Mocked APIs | Push, MR | < 5s |
| **E2E / Roundtrip** | Voller Workflow | Reale APIs | Schedule, Manuell | 30-60s |

---

## Fixture-Architektur

Alle Ebenen verwenden **dieselben Fixture-Daten** aus `tests/fixtures/real_applications.py`.
Die Fixtures basieren auf **echten Bewerbungen** und werden bei neuen Bewerbungstypen erweitert.

```
tests/fixtures/real_applications.py
│
├── RANDSTAD_ARCHIVIERUNG_PROJECT      ← Crawl-Daten
├── RANDSTAD_ARCHIVIERUNG_EXPECTED_MATCH ← Erwartetes Match-Ergebnis
├── RANDSTAD_ARCHIVIERUNG_CSV_ENTRY    ← CSV-Zeile
├── RANDSTAD_ARCHIVIERUNG_DRAFT        ← Email-Draft
├── RANDSTAD_ARCHIVIERUNG_CRM_ISSUE    ← CRM-Issue-Daten
│
├── AI_PROJECT                          ← AI/KI Projekt (parametriert)
├── DEVOPS_PROJECT                      ← DevOps Projekt (parametriert)
└── LOW_MATCH_PROJECT                   ← Negativ-Beispiel
```

**Warum echte Daten?** Synthetische Testdaten verstecken Edge Cases. Echte Projekte
(z.B. mit fehlender Email, unklarem Remote-Anteil, Teilzeit-Auslastung) decken reale
Probleme ab.

---

## Use Cases und Testabdeckung

### UC-1: Bewerbungs-Pipeline (Crawl → Draft → CRM)

| Schritt | Unit Test | Integration Test | E2E |
|---------|-----------|-----------------|-----|
| Crawl: Projekt parsen | ✅ Pflichtfelder, Skills | ✅ JSON-Struktur | ✅ freelancermap live |
| Match: Score berechnen | ✅ Score-Range, Keywords | ✅ Crawl→Match Flow | — |
| QA: Validierung | ✅ Felder, Status, Rate | ✅ Match→QA→Draft | — |
| Draft: Email generieren | ✅ Inhalt, Länge, KI-Intro | ✅ Draft-JSON-Format | ✅ Gmail Draft |
| CRM: Issue erstellen | ✅ Titel, Labels | ✅ API-Payload | ✅ GitLab Issue |

### UC-2: CRM Integrity

| Check | Unit | Integration | E2E |
|-------|------|------------|-----|
| Status-Labels konsistent | ✅ | ✅ | ✅ Weekly Schedule |
| Keine Ghost-Issues | ✅ | — | ✅ |
| Duplikat-Erkennung | ✅ | ✅ CRM API Mock | ✅ |
| Funnel-Metriken | ✅ | — | ✅ Report |

### UC-3: Billing / Invoicing

| Schritt | Unit | Integration | E2E |
|---------|------|------------|-----|
| Timesheet parsen | ✅ | — | — |
| Invoice generieren | ✅ | ✅ PDF erzeugen | — |
| Email versenden | — | ✅ Gmail Mock | ✅ Manuell |

---

## CI-Jobs

```yaml
# Automatisch bei Push/MR
test:unit          → pytest tests/unit/ -m "not integration"
test:coverage      → pytest tests/ --cov=modules --cov=scripts/ci

# Manuell / Schedule
test:integration   → pytest tests/integration/ -m integration
roundtrip:*        → Voller E2E Workflow (CRM + Gmail)
```

### Trigger-Matrix

| Event | Unit | Coverage | Integration | E2E |
|-------|------|----------|-------------|-----|
| Push auf main | ✅ | — | — | — |
| Merge Request | ✅ | ✅ | — | — |
| Schedule (Mo 07:00) | — | — | — | ✅ Health Check |
| Schedule (Mo 07:30) | — | — | — | ✅ Roundtrip |
| `RUN_TESTS=true` | ✅ | — | — | — |
| `TEST_INTEGRATION=true` | — | — | ✅ | — |
| `RUN_ROUNDTRIP_TEST=true` | — | — | — | ✅ |

---

## Neue Tests hinzufügen

### Neuer Use Case

1. **Fixture erstellen** in `tests/fixtures/real_applications.py`
   - Echte Daten verwenden (aus CSV oder Crawler-Output)
   - Erwartete Ergebnisse für jede Pipeline-Stufe definieren

2. **Unit Tests** in `tests/unit/test_<usecase>.py`
   - Jede Stufe isoliert testen
   - Parametrierung für Varianten nutzen

3. **Integration Test** in `tests/integration/test_<pipeline>.py`
   - Stufen-übergreifenden Datenfluss testen
   - APIs mocken, Dateisystem via `tmp_path`

4. **E2E erweitern** (nur wenn nötig)
   - `roundtrip-test.yml` um neuen Check erweitern
   - Cleanup nicht vergessen!

### Checkliste

```
☐ Fixture in tests/fixtures/ mit echten Daten
☐ Unit Tests: min. 3 pro Pipeline-Stufe
☐ Integration Test: Datenfluss zwischen Stufen
☐ Alle Tests lokal grün: pytest tests/ -v
☐ CI-Pipeline grün
☐ Coverage >= 70% für betroffene Module
```

---

## Konventionen

- **Testklassen** nach Use Case benennen: `TestMatchScoring`, `TestCRMIssueCreation`
- **Fixtures** sind die Single Source of Truth — nie Testdaten inline duplizieren
- **Marks**: `@pytest.mark.integration` für alles mit Modul-Interaktion
- **Parametrierung** für Score-Ranges, Projekt-Typen, Status-Werte
- **Assertions** mit aussagekräftigen Messages: `assert score >= 80, f"Got {score}%"`
- **Kein** `print()` in Tests — pytest Output reicht

---

## Metriken

| Metrik | Ziel | Aktuell |
|--------|------|---------|
| Unit Tests | > 80 | ~70 |
| Coverage (modules/) | > 70% | TBD |
| Integration Tests | > 10 | ~10 |
| E2E Success Rate | > 95% | Manuell |
| Test-Laufzeit (Unit) | < 2s | ~0.2s |

---

*Zuletzt aktualisiert: 2026-02-05*
*Maintainer: ops/backoffice*
