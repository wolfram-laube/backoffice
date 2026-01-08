#!/bin/bash
# ══════════════════════════════════════════════════════════════
# GitLab Runner Setup auf GCP (Compute Engine)
# ══════════════════════════════════════════════════════════════
#
# Usage: 
#   ./scripts/setup-gcp-runner.sh                    # Token aus Datei
#   ./scripts/setup-gcp-runner.sh <TOKEN>            # Token direkt
#   ./scripts/setup-gcp-runner.sh <TOKEN> <PROJECT>  # Mit GCP Project
#
# ══════════════════════════════════════════════════════════════

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
TOKEN_FILE="$REPO_ROOT/config/gitlab/runner.token"

# Token: Argument > Datei > Abbruch
if [ -n "$1" ] && [[ "$1" == glrt-* ]]; then
    TOKEN="$1"
    PROJECT_ID="${2:-blauweiss-llc}"
elif [ -f "$TOKEN_FILE" ] && [ -s "$TOKEN_FILE" ] && ! grep -q "^#" "$TOKEN_FILE"; then
    TOKEN=$(cat "$TOKEN_FILE" | tr -d '\n')
    PROJECT_ID="${1:-blauweiss-llc}"
    echo "📄 Token aus $TOKEN_FILE gelesen"
else
    echo "❌ Kein Token gefunden!"
    echo ""
    echo "Option 1: Token in Datei speichern"
    echo "   echo 'glrt-xxx' > config/gitlab/runner.token"
    echo ""
    echo "Option 2: Token als Argument"
    echo "   $0 <TOKEN> [PROJECT_ID]"
    exit 1
fi

ZONE="europe-west3-a"
MACHINE_TYPE="e2-small"
VM_NAME="gitlab-runner"

echo "═══════════════════════════════════════════════════════════════"
echo "  ☁️  GitLab Runner Setup auf GCP"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "  Project:  $PROJECT_ID"
echo "  Zone:     $ZONE"
echo "  Machine:  $MACHINE_TYPE (~\$13/Monat)"
echo "  VM Name:  $VM_NAME"
echo ""

# Check gcloud
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI nicht gefunden!"
    echo "Installieren: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Set project
echo "📋 Setze GCP Projekt..."
gcloud config set project "$PROJECT_ID"

# Enable APIs
echo "🔌 Aktiviere APIs..."
gcloud services enable compute.googleapis.com

# Startup script for VM
STARTUP_SCRIPT=$(cat << 'STARTUP'
#!/bin/bash
apt-get update
apt-get install -y docker.io curl
curl -L "https://packages.gitlab.com/install/repositories/runner/gitlab-runner/script.deb.sh" | bash
apt-get install -y gitlab-runner
usermod -aG docker gitlab-runner
systemctl enable docker
systemctl start docker
STARTUP
)

echo "🖥️  Erstelle VM..."
gcloud compute instances create "$VM_NAME" \
    --zone="$ZONE" \
    --machine-type="$MACHINE_TYPE" \
    --image-family="debian-12" \
    --image-project="debian-cloud" \
    --boot-disk-size="20GB" \
    --tags="gitlab-runner" \
    --metadata="startup-script=$STARTUP_SCRIPT"

echo "⏳ Warte auf VM (60s)..."
sleep 60

echo "📝 Registriere Runner..."
gcloud compute ssh "$VM_NAME" --zone="$ZONE" --command="
    sudo gitlab-runner register \
        --non-interactive \
        --url 'https://gitlab.com' \
        --token '$TOKEN' \
        --description 'gcp-shell' \
        --tag-list 'shell,gcp,linux' \
        --executor 'shell'
    
    sudo gitlab-runner register \
        --non-interactive \
        --url 'https://gitlab.com' \
        --token '$TOKEN' \
        --description 'gcp-docker' \
        --tag-list 'docker,gcp,linux' \
        --executor 'docker' \
        --docker-image 'python:3.11-slim' \
        --docker-privileged
    
    sudo gitlab-runner start
    sudo gitlab-runner list
"

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  ✅ GCP Runner Setup abgeschlossen!"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "  Stoppen: gcloud compute instances stop $VM_NAME --zone=$ZONE"
echo "  Starten: gcloud compute instances start $VM_NAME --zone=$ZONE"
echo ""
