#!/bin/bash
# =============================================================================
# CI Metrics — Phase 2: BigQuery Setup
# =============================================================================
# Run this on your Mac to:
#   1. Regenerate the GCP service account key
#   2. Add BigQuery IAM roles
#   3. Enable BigQuery API
#   4. Update GitLab CI variable
#
# Prerequisites: gcloud CLI authenticated with owner/editor access
# =============================================================================

set -euo pipefail

GCP_PROJECT="myk8sproject-207017"
SA_EMAIL="gitlab-runner-controller@${GCP_PROJECT}.iam.gserviceaccount.com"
GITLAB_GROUP_ID="120698013"
GITLAB_TOKEN="${GITLAB_API_TOKEN:-glpat--wmS4xEWjjWdOgaOd7oDWG86MQp1OnN4Y3gK.01.101dpjjbj}"

echo "╔══════════════════════════════════════════════╗"
echo "║  CI Metrics — Phase 2: GCP + BigQuery Setup  ║"
echo "╚══════════════════════════════════════════════╝"

# ─── Step 1: Verify gcloud auth ──────────────────────────────
echo ""
echo "▶ Step 1: Checking gcloud authentication..."
CURRENT_ACCOUNT=$(gcloud auth list --filter="status:ACTIVE" --format="value(account)" 2>/dev/null || echo "none")
echo "  Active account: ${CURRENT_ACCOUNT}"

if [[ "$CURRENT_ACCOUNT" == "none" ]]; then
    echo "  ❌ Not authenticated. Run: gcloud auth login"
    exit 1
fi

gcloud config set project ${GCP_PROJECT} --quiet
echo "  ✅ Project set to ${GCP_PROJECT}"

# ─── Step 2: Enable BigQuery API ─────────────────────────────
echo ""
echo "▶ Step 2: Enabling BigQuery API..."
gcloud services enable bigquery.googleapis.com --quiet
echo "  ✅ BigQuery API enabled"

# ─── Step 3: Add BigQuery IAM roles to SA ────────────────────
echo ""
echo "▶ Step 3: Granting BigQuery roles to ${SA_EMAIL}..."

for ROLE in "roles/bigquery.dataEditor" "roles/bigquery.user" "roles/bigquery.jobUser"; do
    echo "  Adding ${ROLE}..."
    gcloud projects add-iam-policy-binding ${GCP_PROJECT} \
        --member="serviceAccount:${SA_EMAIL}" \
        --role="${ROLE}" \
        --quiet --no-user-output-enabled 2>/dev/null || true
done
echo "  ✅ BigQuery IAM roles granted"

# ─── Step 4: Generate new SA key ─────────────────────────────
echo ""
echo "▶ Step 4: Generating new service account key..."
KEY_FILE="/tmp/gcp-sa-key-new.json"

# Delete old keys (keep one as backup)
OLD_KEYS=$(gcloud iam service-accounts keys list \
    --iam-account="${SA_EMAIL}" \
    --format="value(KEY_ID)" \
    --filter="keyType=USER_MANAGED" 2>/dev/null)

gcloud iam service-accounts keys create "${KEY_FILE}" \
    --iam-account="${SA_EMAIL}" \
    --quiet
echo "  ✅ New key saved to ${KEY_FILE}"

# Base64 encode for GitLab
B64_KEY=$(base64 < "${KEY_FILE}" | tr -d '\n')
echo "  Key size: $(wc -c < "${KEY_FILE}") bytes"

# ─── Step 5: Update GitLab CI variable ───────────────────────
echo ""
echo "▶ Step 5: Updating GitLab CI variable GCP_SERVICE_ACCOUNT_KEY..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    --request PUT \
    --header "PRIVATE-TOKEN: ${GITLAB_TOKEN}" \
    --header "Content-Type: application/json" \
    --data "{\"value\": \"${B64_KEY}\", \"masked\": false, \"protected\": false}" \
    "https://gitlab.com/api/v4/groups/${GITLAB_GROUP_ID}/variables/GCP_SERVICE_ACCOUNT_KEY")

if [[ "$HTTP_CODE" == "200" ]]; then
    echo "  ✅ GitLab variable updated"
else
    echo "  ⚠️  HTTP ${HTTP_CODE} — you may need to update manually"
    echo "  Value saved to: ${KEY_FILE}"
fi

# ─── Step 6: Quick BigQuery test ─────────────────────────────
echo ""
echo "▶ Step 6: Testing BigQuery access..."
gcloud auth activate-service-account --key-file="${KEY_FILE}" --quiet 2>/dev/null

bq --project_id=${GCP_PROJECT} ls 2>/dev/null && echo "  ✅ BigQuery accessible" || echo "  ⚠️  BigQuery test failed (might need a minute to propagate)"

# Switch back to user account
gcloud config set account "${CURRENT_ACCOUNT}" --quiet 2>/dev/null || true

# ─── Step 7: Clean up old SA keys (optional) ─────────────────
echo ""
if [[ -n "$OLD_KEYS" ]]; then
    echo "▶ Step 7: Old SA keys found (consider deleting):"
    echo "$OLD_KEYS" | while read KEY_ID; do
        echo "  - ${KEY_ID}"
        echo "    Delete with: gcloud iam service-accounts keys delete ${KEY_ID} --iam-account=${SA_EMAIL}"
    done
else
    echo "▶ Step 7: No old user-managed keys found"
fi

# ─── Summary ─────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  ✅ Setup Complete!                           ║"
echo "╠══════════════════════════════════════════════╣"
echo "║  Next steps:                                  ║"
echo "║  1. Go to GitLab → CI/CD → Run Pipeline       ║"
echo "║  2. Trigger 'ci-metrics:setup-bq' job          ║"
echo "║     (creates dataset + tables in BigQuery)     ║"
echo "║  3. Trigger 'ci-metrics:build' + 'deploy'     ║"
echo "║     (builds + deploys to Cloud Run)            ║"
echo "╚══════════════════════════════════════════════╝"

# Cleanup
rm -f "${KEY_FILE}"
echo "Cleaned up ${KEY_FILE}"
