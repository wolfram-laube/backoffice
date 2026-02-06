#!/usr/bin/env bash
# =============================================================================
# MAB Reporter - Reports CI job outcomes to Runner Bandit Service
# =============================================================================
# Usage in .gitlab-ci.yml:
#   after_script:
#     - bash scripts/mab_report.sh
#
# Required CI Variables:
#   CI_JOB_STATUS     (auto-set by GitLab)
#   CI_JOB_DURATION   (auto-set by GitLab - only in after_script!)
#   CI_RUNNER_DESCRIPTION (auto-set by GitLab)
#   MAB_SERVICE_URL   (set in CI variables or default)
# =============================================================================

MAB_URL="${MAB_SERVICE_URL:-https://runner-bandit-m5cziijwqa-lz.a.run.app}"
JOB_STATUS="${CI_JOB_STATUS:-unknown}"
DURATION="${CI_JOB_DURATION:-0}"
RUNNER="${CI_RUNNER_DESCRIPTION:-unknown}"
JOB_NAME="${CI_JOB_NAME:-unknown}"
PROJECT="${CI_PROJECT_NAME:-unknown}"

# Only report for known statuses
if [[ "$JOB_STATUS" != "success" && "$JOB_STATUS" != "failed" ]]; then
    echo "[MAB] Skipping report: status=$JOB_STATUS"
    exit 0
fi

SUCCESS="false"
[[ "$JOB_STATUS" == "success" ]] && SUCCESS="true"

echo "[MAB] Reporting: runner=$RUNNER status=$JOB_STATUS duration=${DURATION}s job=$JOB_NAME"

RESPONSE=$(curl -sf -X POST "${MAB_URL}/update" \
    -H "Content-Type: application/json" \
    -d "{
        \"runner\": \"${RUNNER}\",
        \"success\": ${SUCCESS},
        \"duration\": ${DURATION},
        \"job_name\": \"${JOB_NAME}\",
        \"project\": \"${PROJECT}\"
    }" 2>&1) || true

if [[ -n "$RESPONSE" ]]; then
    echo "[MAB] Response: $RESPONSE"
else
    echo "[MAB] Warning: Could not reach MAB service (non-fatal)"
fi
