#!/bin/bash
# ══════════════════════════════════════════════════════════════
# GitLab Runner Setup Script für macOS
# ══════════════════════════════════════════════════════════════

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
TOKEN_FILE="$REPO_ROOT/config/gitlab/runner.token"

# Token: Argument > Datei
if [ -n "$1" ]; then
    TOKEN="$1"
elif [ -f "$TOKEN_FILE" ] && [ -s "$TOKEN_FILE" ] && ! grep -q "^#" "$TOKEN_FILE"; then
    TOKEN=$(cat "$TOKEN_FILE" | tr -d '\n')
    echo "📄 Token aus $TOKEN_FILE gelesen"
else
    echo "❌ Kein Token gefunden!"
    exit 1
fi

echo "═══════════════════════════════════════════════════════════════"
echo "  🏃 GitLab Runner Setup"
echo "═══════════════════════════════════════════════════════════════"

# Install
command -v gitlab-runner &> /dev/null || brew install gitlab-runner

# Stop existing
gitlab-runner stop 2>/dev/null || true

# Register Shell Runner (Tags werden in GitLab UI gesetzt!)
echo "📝 Registriere Shell Runner..."
gitlab-runner register \
    --non-interactive \
    --url "https://gitlab.com" \
    --token "$TOKEN" \
    --executor "shell" \
    --description "mac-shell"

echo "✓ Shell Runner registriert"

# Install & Start als Service
echo "🔧 Installiere als Service..."
gitlab-runner install --user="$(whoami)" 2>/dev/null || true
gitlab-runner start

echo ""
echo "═══════════════════════════════════════════════════════════════"
gitlab-runner list
echo "═══════════════════════════════════════════════════════════════"
echo "✅ Setup abgeschlossen!"
echo ""
echo "Runner startet jetzt automatisch bei Login."
echo ""
echo "Nützliche Befehle:"
echo "  gitlab-runner status"
echo "  gitlab-runner list"
echo "  gitlab-runner stop"
echo "  gitlab-runner start"
echo ""
