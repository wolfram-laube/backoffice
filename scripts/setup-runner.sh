#!/bin/bash
# ══════════════════════════════════════════════════════════════
# GitLab Runner Setup Script für macOS
# ══════════════════════════════════════════════════════════════
#
# Usage: 
#   ./scripts/setup-runner.sh              # Liest Token aus config/gitlab/runner.token
#   ./scripts/setup-runner.sh <TOKEN>      # Oder Token direkt übergeben
#
# ══════════════════════════════════════════════════════════════

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
TOKEN_FILE="$REPO_ROOT/config/gitlab/runner.token"

# Token: Argument > Datei > Abbruch
if [ -n "$1" ]; then
    TOKEN="$1"
elif [ -f "$TOKEN_FILE" ] && [ -s "$TOKEN_FILE" ] && ! grep -q "^#" "$TOKEN_FILE"; then
    TOKEN=$(cat "$TOKEN_FILE" | tr -d '\n')
    echo "📄 Token aus $TOKEN_FILE gelesen"
else
    echo "❌ Kein Token gefunden!"
    echo ""
    echo "Option 1: Token in Datei speichern"
    echo "   echo 'glrt-xxx' > config/gitlab/runner.token"
    echo ""
    echo "Option 2: Token als Argument"
    echo "   $0 <TOKEN>"
    echo ""
    echo "Token holen: https://gitlab.com/wolfram_laube/blauweiss_llc/freelancer-admin/-/settings/ci_cd"
    exit 1
fi

GITLAB_URL="https://gitlab.com"

echo "═══════════════════════════════════════════════════════════════"
echo "  🏃 GitLab Runner Setup für freelancer-admin"
echo "═══════════════════════════════════════════════════════════════"

# Install gitlab-runner
echo "📦 Installiere gitlab-runner..."
command -v gitlab-runner &> /dev/null || brew install gitlab-runner

# Stop existing
gitlab-runner stop 2>/dev/null || true

# Register Shell Runner
echo "📝 Registriere Shell Runner..."
gitlab-runner register \
    --non-interactive \
    --url "$GITLAB_URL" \
    --token "$TOKEN" \
    --description "mac-shell" \
    --tag-list "shell,macos,local" \
    --executor "shell"

echo "✓ Shell Runner registriert"

# Docker Runner optional
echo ""
read -p "🐳 Docker Runner auch einrichten? [y/N] " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]] && command -v docker &> /dev/null; then
    gitlab-runner register \
        --non-interactive \
        --url "$GITLAB_URL" \
        --token "$TOKEN" \
        --description "mac-docker" \
        --tag-list "docker,macos" \
        --executor "docker" \
        --docker-image "python:3.11-slim"
    echo "✓ Docker Runner registriert"
fi

# Install & Start
gitlab-runner install --user="$(whoami)" 2>/dev/null || true
gitlab-runner start

echo ""
echo "═══════════════════════════════════════════════════════════════"
gitlab-runner list
echo "═══════════════════════════════════════════════════════════════"
echo "✅ Setup abgeschlossen!"
echo ""
echo "Check: https://gitlab.com/wolfram_laube/blauweiss_llc/freelancer-admin/-/settings/ci_cd"
