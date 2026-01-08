# GitLab Credentials

## Personal Access Token (PAT)
Für API-Zugriff (Repo-Operationen, Commits, etc.)

**Datei:** `pat.token`

Erstellen: https://gitlab.com/-/user_settings/personal_access_tokens
Scopes: `api`, `write_repository`

## Runner Registration Token
Für Runner-Registrierung auf Mac/GCP

**Datei:** `runner.token`

Holen: https://gitlab.com/wolfram_laube/blauweiss_llc/freelancer-admin/-/settings/ci_cd
→ Runners → "New project runner"

## Verwendung

```bash
# PAT für API calls
export GITLAB_PAT=$(cat config/gitlab/pat.token)

# Runner Setup
./scripts/setup-runner.sh $(cat config/gitlab/runner.token)
```

## Revoken

Falls kompromittiert:
- PAT: https://gitlab.com/-/user_settings/personal_access_tokens → Revoke
- Runner Token: GitLab UI → Runners → Reset registration token
