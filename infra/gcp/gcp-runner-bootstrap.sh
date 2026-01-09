#!/bin/bash
# ══════════════════════════════════════════════════════════════
# GCP GitLab Runner - Idempotent Bootstrap
# ══════════════════════════════════════════════════════════════
# Run on VM to ensure correct state. Safe to run multiple times.
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
    python3
    python3-venv
    python3-pip
    python3-dev
    build-essential
    git
    curl
    wget
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
# 4. Install as systemd service (AUTO-START ON BOOT!)
# ─────────────────────────────────────────────────────────────
echo "🔧 Installing gitlab-runner as systemd service..."

if [ ! -f /etc/systemd/system/gitlab-runner.service ]; then
    gitlab-runner install --user=gitlab-runner
    echo "   ✓ Systemd service installed"
else
    echo "   ✓ Systemd service already exists"
fi

systemctl daemon-reload
systemctl enable gitlab-runner
systemctl start gitlab-runner

# ─────────────────────────────────────────────────────────────
# 5. Register Runner (if token provided)
# ─────────────────────────────────────────────────────────────
if [ -n "$RUNNER_TOKEN" ]; then
    echo "🔑 Registering runner..."
    
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
# 6. Restart to apply all changes
# ─────────────────────────────────────────────────────────────
echo "🔄 Restarting gitlab-runner service..."
systemctl restart gitlab-runner

# ─────────────────────────────────────────────────────────────
# 7. Verify
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
echo "Service status:"
systemctl status gitlab-runner --no-pager | head -5
echo ""
echo "Registered runners:"
gitlab-runner list
echo ""
