# 🔀 Git Workflow - Best Practices

> Kanonischer Workflow für Features, Bugs und Hotfixes im blauweiss_llc GitLab.

**Branch Protection:** `main` ist geschützt - kein direkter Push, nur via Merge Request.

---

## Branch Naming Convention

| Type | Pattern | Example |
|------|---------|---------|
| **Feature** | `feat/<short-description>` | `feat/mab-service` |
| **Bug Fix** | `fix/<issue-or-desc>` | `fix/billing-calculation` |
| **Hotfix** | `hotfix/<issue-or-desc>` | `hotfix/critical-auth-bug` |
| **Docs** | `docs/<topic>` | `docs/api-reference` |
| **Refactor** | `refactor/<scope>` | `refactor/ci-pipeline` |
| **Chore** | `chore/<task>` | `chore/update-deps` |

---

## 🚀 Feature Workflow

```bash
# 1. Create feature branch from main
git checkout main
git pull origin main
git checkout -b feat/my-feature

# 2. Work on feature (commit often)
git add .
git commit -m "feat(scope): description"

# 3. Push branch
git push -u origin feat/my-feature

# 4. Create MR via GitLab UI or API
#    - Title: "feat(scope): My Feature"
#    - Description: What, Why, How
#    - Labels: relevant labels
#    - Link related issues: "Closes #123"

# 5. After approval, merge via GitLab (squash recommended)
# 6. Branch auto-deleted after merge
```

---

## 🐛 Bug Fix Workflow

```bash
# 1. Create fix branch
git checkout main && git pull
git checkout -b fix/issue-123-description

# 2. Fix the bug
git add .
git commit -m "fix(scope): description

Fixes #123"

# 3. Push and create MR
git push -u origin fix/issue-123-description

# MR Title: "fix(scope): Brief description"
# Link: "Fixes #123" or "Closes #123"
```

---

## 🔥 Hotfix Workflow (Production Critical)

```bash
# 1. Create hotfix from main (or tag if needed)
git checkout main && git pull
git checkout -b hotfix/critical-issue

# 2. Minimal fix only
git add .
git commit -m "hotfix: critical auth bypass

BREAKING: Immediate deployment required"

# 3. Push immediately, request expedited review
git push -u origin hotfix/critical-issue

# 4. Create MR with "Priority::Critical" label
# 5. Get review (can be post-merge for true emergencies)
# 6. Merge and deploy immediately
```

---

## Commit Message Convention

Follows [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

**Types:**
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation only
- `refactor` - Code change (no feature/fix)
- `test` - Adding tests
- `chore` - Maintenance tasks
- `ci` - CI/CD changes
- `hotfix` - Critical production fix

**Examples:**
```
feat(billing): add invoice PDF generation

fix(crm): correct stale issue detection logic

Fixes #19

docs(api): update endpoint documentation

ci(cloud-run): add skopeo copy stage for registry sync
```

---

## Merge Request Checklist

- [ ] Branch from `main` (up to date)
- [ ] Descriptive branch name (`feat/`, `fix/`, etc.)
- [ ] Conventional commit messages
- [ ] Tests pass (if applicable)
- [ ] Documentation updated (if applicable)
- [ ] Related issues linked
- [ ] Labels assigned
- [ ] Reviewer assigned (if required)

---

## Labels

| Category | Labels |
|----------|--------|
| **Type** | `feat`, `fix`, `docs`, `refactor`, `chore` |
| **Priority** | `Priority::Critical`, `Priority::High`, `Priority::Normal` |
| **Status** | `in-progress`, `review`, `blocked` |
| **Domain** | `billing`, `crm`, `infrastructure`, `ai/ml` |

---

## Quick Reference

```bash
# Start feature
git checkout main && git pull && git checkout -b feat/NAME

# Start fix
git checkout main && git pull && git checkout -b fix/NAME

# Commit
git commit -m "type(scope): message"

# Push & MR
git push -u origin BRANCH_NAME
# → Create MR in GitLab

# After merge, cleanup local
git checkout main && git pull && git branch -d BRANCH_NAME
```

---

## Related

- [GitLab Flow](https://docs.gitlab.com/ee/topics/gitlab_flow.html)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Semantic Versioning](https://semver.org/)
