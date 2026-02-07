# NEXT SESSION PROMPT

Lies zuerst das Handover:
- `docs/handover/HANDOVER_HOUSEKEEPING_08_02_2026.md`

## Kontext

Grosse Housekeeping-Session: 9 Issues geschlossen (12 → 3), 2 MRs aufgeloest,
CI-Fixes applied, MAB Cloud Run Pipeline gemerged, GitHub Mirror fuer corporate
eingerichtet. Repo ist sauber.

## Verbleibende offene Issues (3)

| Issue | Title | Notes |
|-------|-------|-------|
| #29 | [EPIC] GitHub Mirroring - Colab/Jupyter Integration | #31 done, backoffice mirror optional |
| #27 | [EPIC] Neurosymbolic AI Runner Selection | Ongoing |
| #26 | [NSAI] JKU Bachelor Paper Draft | Supervisor-Name TBD |

## Moegliche Aufgaben

1. **Supervisor-Name im Paper** (wenn bekannt)
   - Zeile 657 in `docs/publications/nsai-runner-selection-2026/nsai_paper.qmd`
   - Acknowledgements TODO ersetzen
   - Auch in LaTeX-Version (falls separat gepflegt)

2. **EPIC #29 updaten**
   - corporate → GitHub Mirror ist live (https://github.com/wolfram-laube/corporate)
   - Pruefen ob backoffice auch gespiegelt werden soll
   - EPIC #29 Status-Comment posten

3. **GitHub Mirror verifizieren**
   - corporate sync erfolgreich (2026-02-07T13:14)
   - Content auf GitHub pruefen

4. **Quarto Freeze-Cache committen**
   - Nach naechstem vollstaendigen `quarto render`
   - `_freeze/` Ordner committen fuer schnelle Rebuilds

5. **Bewerbungen / Job Hunt**
   - CSV-Tracking aktualisieren
   - Neue Leads pruefen

6. **Pipelines monitoren**
   - CI-Fixes (090f3cd6) sollten #41/#42/#43 geloest haben
   - Naechster scheduled Run beobachten

## Credentials

- GitLab PAT: `glpat--wmS4xEWjjWdOgaOd7oDWG86MQp1OnN4Y3gK.01.101dpjjbj`
- GitHub PAT: `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`
- User: wolfram.laube (ID: 1349601)
- Repos: backoffice=77555895, corporate=77075415, CLARISSA=77260390
