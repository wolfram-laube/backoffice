# ADR-030: Applications Pipeline Migration (CLARISSA → Backoffice)

**Status:** Accepted  
**Date:** 2026-02-04  
**Author:** Wolfram Laube  

## Context

The `blauweiss_llc` GitLab group contains multiple repositories:

- **CLARISSA** (`projects/clarissa`): AI/NLP research project for Conversational Language Agent for Reservoir Simulation
- **Backoffice** (`ops/backoffice`): Business operations (CRM, invoicing, timesheets, applications)
- **CRM** (`ops/crm`): GitLab Issues as CRM database

Over time, several business operations scripts ended up in the CLARISSA repository:
- `applications_crawl.py` - Freelancermap job crawler
- `applications_match.py` - Skill matching and scoring
- `applications_drafts.py` - Email draft generation
- `applications_qa.py` - Application validation
- `crm_integrity_check.py` - CRM health checks

These scripts have **nothing to do with reservoir simulation research**.

## Decision

**Migrate all business operations scripts from CLARISSA to Backoffice.**

### Rationale

1. **Separation of Concerns**: Research vs. Operations should be separate
2. **Independent Lifecycles**: CLARISSA has conference deadlines, Backoffice has business SLAs
3. **Test Isolation**: Each repo gets its own focused test suite
4. **Team Access**: Operations team doesn't need access to research code
5. **CI/CD Clarity**: Pipeline includes are cleaner when domain-focused

## Consequences

### Positive
- Clear repository ownership
- Focused test suites per domain
- Simpler CI/CD configuration
- Better onboarding for team members

### Negative
- One-time migration effort
- Need to update documentation
- Potential for broken references (mitigated by keeping pipeline configs in backoffice)

### Neutral
- Both repos need `scripts/ci/` directory
- Group-level labels/variables remain shared

## Implementation

1. ✅ Copy scripts to backoffice (commit `71dadc94`)
2. ✅ Remove scripts from CLARISSA (commit `59a5898d`)
3. ✅ Add test suite for migrated scripts (commit `abaa8c69`)
4. ✅ Update CI configuration (commit `db676088`)

## Related

- Epic #14: Applications Pipeline Migration
- Issues #15-#18: Migration tasks
