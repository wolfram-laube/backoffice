# Session Index

Durchsuchbarer Index aller Claude-Sessions. Keywords für schnelles `grep`.

| Date | Topic | Keywords | Issues | Handover |
|------|-------|----------|--------|----------|
| 2026-02-04 | CI Runner Migration + MAB | ci, runner, mab, ucb1, thompson, nsai, bandit, gcp, docker-any | #27 #28 | [HANDOVER_PROFILES_CI](./HANDOVER_PROFILES_CI_04_02_2026.md) |
| 2026-02-04 | Billing Tests + Schedule Migration | billing, tests, pytest, schedule, clarissa | | [HANDOVER_BILLING_TESTS](./HANDOVER_BILLING_TESTS_04_02_2026.md) |
| 2026-02-04 | Profile Module Migration | profile, migration, consolidation | | [HANDOVER_MIGRATION](./HANDOVER_MIGRATION_04_02_2026.md) |
| 2026-02-04 | Test Suite Setup | tests, pytest, fixtures, billing | | [HANDOVER_TESTSUITE](./HANDOVER_TESTSUITE_04_02_2026.md) |
| 2026-02-03 | Runner Fallback System | runner, fallback, gcp, auto-start, clarissa | | [HANDOVER_RUNNER_FALLBACK](./HANDOVER_RUNNER_FALLBACK_03_02_2026.md) |
| 2026-02-03 | CI Refactor | ci, refactor, yaml, pipeline | | [HANDOVER_CI_REFACTOR](./HANDOVER_CI_REFACTOR_03_02_2026.md) |
| 2026-02-03 | GCP Stockholm Migration | gcp, stockholm, nordic, vm, europe-north2 | #12 | [HANDOVER_GCP_STOCKHOLM](./HANDOVER_GCP_STOCKHOLM_03_02_2026.md) |
| 2026-02-02 | Portal Setup | portal, mkdocs, pages, gitlab-pages | | [HANDOVER_PORTAL](./HANDOVER_PORTAL_02_02_2026.md) |

---

## Quick Search

```bash
# Find sessions about MAB
grep -i "mab" docs/handover/INDEX.md

# Find all GCP-related work
grep -i "gcp" docs/handover/INDEX.md
```

## Adding New Entries

Append new sessions at the top of the table. Format:
```
| YYYY-MM-DD | Short Topic | keyword1, keyword2, ... | #issue1 #issue2 | [HANDOVER_NAME](./HANDOVER_NAME_DD_MM_YYYY.md) |
```

---

## Next Chat

→ **[NEXT_CHAT_TEMPLATE.md](./NEXT_CHAT_TEMPLATE.md)** - Copy & paste für Session-Übergang
