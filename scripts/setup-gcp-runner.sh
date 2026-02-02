#!/bin/bash
# ══════════════════════════════════════════════════════════════
# GCP GitLab Runner - VM Setup (IaC Version)
# ══════════════════════════════════════════════════════════════
#
# Creates/updates GCP VM with GitLab Runner.
# Idempotent - safe to run multiple times.
#
# Usage:
#   ./scripts/setup-gcp-runner.sh <RUNNER_TOKEN> [PROJECT_ID]
#
# Environment variables:
#   GCP_PROJECT   - GCP project ID (default: myk8sproject-207017)
#   GCP_ZONE      - Zone (default: europe-west3-a)
#   GCP_MACHINE   - Machine type (default: e2-small)
#   VM_NAME       - VM name (default: gitlab-runner)
#
# ══════════════════════════════════════════════════════════════

set -e

# ─────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────
RUNNER_TOKEN="${1:-}"
GCP_PROJECT="${2:-${GCP_PROJECT:-myk8sproject-207017}}"
GCP_ZONE="${GCP_ZONE:-europe-west3-a}"
GCP_MACHINE="${GCP_MACHINE:-e2-small}"
VM_NAME="${VM_NAME:-gitlab-runner}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
CLOUD_INIT="$REPO_ROOT/infra/gcp/cloud-init.yaml"
BOOTSTRAP="$REPO_ROOT/infra/gcp/gcp-runner-bootstrap.sh"

# ─────────────────────────────────────────────────────────────
# Banner
# ─────────────────────────────────────────────────────────────
echo "═══════════════════════════════════════════════════════════"
echo "  ☁️  GitLab Runner Setup auf GCP"
echo "═══════════════════════════════════════════════════════════"
echo "  Project:  $GCP_PROJECT"
echo "  Zone:     $GCP_ZONE"
echo "  Machine:  $GCP_MACHINE (~\$13/Monat)"
echo "  VM Name:  $VM_NAME"
echo ""

# ─────────────────────────────────────────────────────────────
# Validate
# ─────────────────────────────────────────────────────────────
if [ -z "$RUNNER_TOKEN" ]; then
    # Try to read from file
    TOKEN_FILE="$REPO_ROOT/config/gitlab/runner-gcp.token"
    if [ -f "$TOKEN_FILE" ]; then
        RUNNER_TOKEN=$(cat "$TOKEN_FILE")
        echo "📋 Token aus $TOKEN_FILE gelesen"
    else
        echo "❌ Kein Token angegeben!"
        echo ""
        echo "Usage: $0 <REGISTRATION_TOKEN> [PROJECT_ID]"
        echo ""
        echo "Token holen von:"
        echo "https://gitlab.com/wolfram_laube/blauweiss_llc/ops/backoffice/-/settings/ci_cd"
        exit 1
    fi
fi

# ─────────────────────────────────────────────────────────────
# GCP Setup
# ─────────────────────────────────────────────────────────────
echo "📋 Setze GCP Projekt..."
gcloud config set project "$GCP_PROJECT"

echo "🔌 Aktiviere APIs..."
gcloud services enable compute.googleapis.com --quiet

# ─────────────────────────────────────────────────────────────
# Check if VM exists
# ─────────────────────────────────────────────────────────────
VM_EXISTS=$(gcloud compute instances list --filter="name=$VM_NAME" --format="value(name)" 2>/dev/null || true)

if [ -n "$VM_EXISTS" ]; then
    echo "🖥️  VM existiert bereits"
    
    # Check if running
    VM_STATUS=$(gcloud compute instances describe "$VM_NAME" --zone="$GCP_ZONE" --format="value(status)")
    
    if [ "$VM_STATUS" != "RUNNING" ]; then
        echo "   Starting VM..."
        gcloud compute instances start "$VM_NAME" --zone="$GCP_ZONE" --quiet
        echo "   ⏳ Warte auf Boot (30s)..."
        sleep 30
    fi
else
    echo "🖥️  Erstelle VM..."
    
    # Create VM with cloud-init
    gcloud compute instances create "$VM_NAME" \
        --zone="$GCP_ZONE" \
        --machine-type="$GCP_MACHINE" \
        --image-family=debian-12 \
        --image-project=debian-cloud \
        --boot-disk-size=20GB \
        --boot-disk-type=pd-standard \
        --metadata-from-file=user-data="$CLOUD_INIT" \
        --tags=gitlab-runner \
        --quiet
    
    echo "⏳ Warte auf Cloud-Init (90s)..."
    sleep 90
fi

# ─────────────────────────────────────────────────────────────
# Run Bootstrap (ensures correct state)
# ─────────────────────────────────────────────────────────────
echo "🔧 Running bootstrap on VM..."

gcloud compute scp "$BOOTSTRAP" "$VM_NAME:/tmp/bootstrap.sh" --zone="$GCP_ZONE" --quiet
gcloud compute ssh "$VM_NAME" --zone="$GCP_ZONE" --command="sudo bash /tmp/bootstrap.sh '$RUNNER_TOKEN'" --quiet

# ─────────────────────────────────────────────────────────────
# Done
# ─────────────────────────────────────════════════════════════
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  ✅ GCP Runner Setup Complete!"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Get external IP
EXTERNAL_IP=$(gcloud compute instances describe "$VM_NAME" --zone="$GCP_ZONE" --format="value(networkInterfaces[0].accessConfigs[0].natIP)")
echo "  VM:     $VM_NAME"
echo "  IP:     $EXTERNAL_IP"
echo "  SSH:    gcloud compute ssh $VM_NAME --zone=$GCP_ZONE"
echo ""
echo "  Runner sollte in GitLab sichtbar sein:"
echo "  https://gitlab.com/wolfram_laube/blauweiss_llc/ops/backoffice/-/settings/ci_cd"
echo ""
