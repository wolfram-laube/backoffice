#!/bin/bash
# GitLab Runner Setup Script für macOS
# Usage: ./scripts/setup-runner.sh <REGISTRATION_TOKEN>

set -e

TOKEN="${1:-}"
GITLAB_URL="https://gitlab.com"

echo "═══════════════════════════════════════════════════════════════"
echo "  🏃 GitLab Runner Setup für freelancer-admin"
echo "═══════════════════════════════════════════════════════════════"

if [ -z "$TOKEN" ]; then
    echo "❌ Kein Token angegeben!"
    echo ""
    echo "Usage: $0 <REGISTRATION_TOKEN>"
    echo ""
    echo "Token holen von:"
    echo "https://gitlab.com/wolfram_laube/blauweiss_llc/freelancer-admin/-/settings/ci_cd"
    exit 1
fi

# Install gitlab-runner
echo "📦 Installiere gitlab-runner..."
command -v gitlab-runner &> /dev/null || brew install gitlab-runner

# Stop existing
gitlab-runner stop 2>/dev/null || true

# Register Shell Runner
echo "📝 Registriere Shell Runner..."
gitlab-runner register     --non-interactive     --url "$GITLAB_URL"     --token "$TOKEN"     --description "mac-shell"     --tag-list "shell,macos,local"     --executor "shell"

echo "✓ Shell Runner registriert"

# Docker Runner optional
echo ""
read -p "🐳 Docker Runner auch einrichten? [y/N] " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]] && command -v docker &> /dev/null; then
    gitlab-runner register         --non-interactive         --url "$GITLAB_URL"         --token "$TOKEN"         --description "mac-docker"         --tag-list "docker,macos"         --executor "docker"         --docker-image "python:3.11-slim"
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
