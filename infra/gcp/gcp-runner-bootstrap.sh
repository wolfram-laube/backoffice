#!/bin/bash
# ══════════════════════════════════════════════════════════════
# GCP GitLab Runner - Idempotent Bootstrap
# ══════════════════════════════════════════════════════════════
# Run on VM to ensure correct state. Safe to run multiple times.
#
# Usage (from Mac):
#   gcloud compute ssh gitlab-runner --zone=europe-west3-a \
#       --command="curl -sL https://gitlab.com/.../bootstrap.sh | sudo bash"
#
# Or copy to VM and run:
#   sudo ./gcp-runner-bootstrap.sh [RUNNER_TOKEN]
# ══════════════════════════════════════════════════════════════

set -e

RUNNER_TOKEN="${1:-}"
GITLAB_URL="https://gitlab.com"
RUNNER_NAME="gcp-shell"

echo "═══════════════════════════════════════════════════════════"
echo "  🔧 GCP Runner Bootstrap"
echo "═══════════════════════════════════════════════════════════"

# ─────────────────────────────────────────────────────────────
# 1. System Packages
# ─────────────────────────────────────────────────────────────
echo "📦 Installing system packages..."

apt-get update -qq

PACKAGES=(
    # Python
    python3
    python3-venv
    python3-pip
    python3-dev
    # Build tools
    build-essential
    git
    curl
    wget
    # Docker dependencies
    ca-certificates
    gnupg
    lsb-release
)

for pkg in "${PACKAGES[@]}"; do
    if ! dpkg -l | grep -q "^ii  $pkg "; then
        echo "   Installing $pkg..."
        apt-get install -y -qq "$pkg"
    else
        echo "   ✓ $pkg already installed"
    fi
done

# ─────────────────────────────────────────────────────────────
# 2. Docker
# ─────────────────────────────────────────────────────────────
echo "🐳 Setting up Docker..."

if ! command -v docker &> /dev/null; then
    echo "   Installing Docker..."
    curl -fsSL https://get.docker.com | sh
else
    echo "   ✓ Docker already installed"
fi

# Ensure gitlab-runner user can use Docker
if id gitlab-runner &>/dev/null; then
    usermod -aG docker gitlab-runner 2>/dev/null || true
fi

systemctl enable docker
systemctl start docker

# ─────────────────────────────────────────────────────────────
# 3. GitLab Runner
# ─────────────────────────────────────────────────────────────
echo "🏃 Setting up GitLab Runner..."

if ! command -v gitlab-runner &> /dev/null; then
    echo "   Installing GitLab Runner..."
    curl -L "https://packages.gitlab.com/install/repositories/runner/gitlab-runner/script.deb.sh" | bash
    apt-get install -y gitlab-runner
else
    echo "   ✓ GitLab Runner already installed"
fi

# ─────────────────────────────────────────────────────────────
# 4. Register Runner (if token provided)
# ─────────────────────────────────────────────────────────────
if [ -n "$RUNNER_TOKEN" ]; then
    echo "🔑 Registering runner..."
    
    # Check if already registered
    if gitlab-runner list 2>&1 | grep -q "$RUNNER_NAME"; then
        echo "   ✓ Runner already registered"
    else
        gitlab-runner register \
            --non-interactive \
            --url "$GITLAB_URL" \
            --token "$RUNNER_TOKEN" \
            --executor "shell" \
            --description "$RUNNER_NAME"
        echo "   ✓ Runner registered"
    fi
fi

# ─────────────────────────────────────────────────────────────
# 5. Start Runner Service
# ─────────────────────────────────────────────────────────────
echo "🚀 Starting runner service..."

gitlab-runner start || true
systemctl enable gitlab-runner
systemctl start gitlab-runner

# ─────────────────────────────────────────────────────────────
# 6. Verify
# ─────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  ✅ Bootstrap Complete!"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "Installed versions:"
echo "  Python:        $(python3 --version 2>&1)"
echo "  Docker:        $(docker --version 2>&1)"
echo "  GitLab Runner: $(gitlab-runner --version 2>&1 | head -1)"
echo ""
echo "Runner status:"
gitlab-runner list
echo ""
