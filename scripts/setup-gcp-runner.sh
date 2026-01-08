#!/bin/bash
# ══════════════════════════════════════════════════════════════
# GitLab Runner Setup auf GCP (Compute Engine)
# ══════════════════════════════════════════════════════════════
#
# Erstellt eine kleine VM mit Docker + GitLab Runner
#
# Voraussetzungen:
#   - gcloud CLI installiert & authentifiziert
#   - GCP Projekt existiert
#   - Billing aktiviert
#
# Usage: 
#   ./scripts/setup-gcp-runner.sh <REGISTRATION_TOKEN> [PROJECT_ID]
#
# ══════════════════════════════════════════════════════════════

set -e

TOKEN="${1:-}"
PROJECT_ID="${2:-blauweiss-llc}"
ZONE="europe-west3-a"  # Frankfurt - nah an Wien
MACHINE_TYPE="e2-small"  # ~$13/Monat, reicht für CI/CD
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

if [ -z "$TOKEN" ]; then
    echo "❌ Kein Token angegeben!"
    echo ""
    echo "Usage: $0 <REGISTRATION_TOKEN> [PROJECT_ID]"
    echo ""
    echo "Token holen von:"
    echo "https://gitlab.com/wolfram_laube/blauweiss_llc/freelancer-admin/-/settings/ci_cd"
    exit 1
fi

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

# Create startup script
STARTUP_SCRIPT=$(cat << 'STARTUP'
#!/bin/bash
set -e

# Install Docker
apt-get update
apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release
curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io

# Install GitLab Runner
curl -L "https://packages.gitlab.com/install/repositories/runner/gitlab-runner/script.deb.sh" | bash
apt-get install -y gitlab-runner

# Add gitlab-runner to docker group
usermod -aG docker gitlab-runner
STARTUP
)

echo "🖥️  Erstelle VM..."
gcloud compute instances create "$VM_NAME" \
    --zone="$ZONE" \
    --machine-type="$MACHINE_TYPE" \
    --image-family="debian-12" \
    --image-project="debian-cloud" \
    --boot-disk-size="20GB" \
    --boot-disk-type="pd-standard" \
    --tags="gitlab-runner" \
    --metadata="startup-script=$STARTUP_SCRIPT" \
    --scopes="https://www.googleapis.com/auth/cloud-platform"

echo "⏳ Warte auf VM Startup (60s)..."
sleep 60

# Register runners via SSH
echo "📝 Registriere Runner..."
gcloud compute ssh "$VM_NAME" --zone="$ZONE" --command="
    # Shell Runner
    sudo gitlab-runner register \
        --non-interactive \
        --url 'https://gitlab.com' \
        --token '$TOKEN' \
        --description 'gcp-shell' \
        --tag-list 'shell,gcp,linux' \
        --executor 'shell'
    
    # Docker Runner
    sudo gitlab-runner register \
        --non-interactive \
        --url 'https://gitlab.com' \
        --token '$TOKEN' \
        --description 'gcp-docker' \
        --tag-list 'docker,gcp,linux' \
        --executor 'docker' \
        --docker-image 'python:3.11-slim' \
        --docker-privileged
    
    # Start runner
    sudo gitlab-runner start
    sudo gitlab-runner list
"

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  ✅ GCP Runner Setup abgeschlossen!"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "  VM: $VM_NAME ($ZONE)"
echo "  Runner: gcp-shell, gcp-docker"
echo ""
echo "  Kosten: ~\$13/Monat (e2-small, 24/7)"
echo ""
echo "  SSH Zugang:"
echo "    gcloud compute ssh $VM_NAME --zone=$ZONE"
echo ""
echo "  Stoppen (spart Geld):"
echo "    gcloud compute instances stop $VM_NAME --zone=$ZONE"
echo ""
echo "  Starten:"
echo "    gcloud compute instances start $VM_NAME --zone=$ZONE"
echo ""
echo "  Löschen:"
echo "    gcloud compute instances delete $VM_NAME --zone=$ZONE"
echo ""
