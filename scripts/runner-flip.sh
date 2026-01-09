#!/bin/bash
# ══════════════════════════════════════════════════════════════
# Runner Flip-Flop: Mac ↔ GCP
# ══════════════════════════════════════════════════════════════

# Full paths for launchd/sleepwatcher compatibility
BREW="/usr/local/bin/brew"
GCLOUD="/usr/local/bin/gcloud"

# Fallback paths (Intel vs Apple Silicon)
[ ! -f "$BREW" ] && BREW="/opt/homebrew/bin/brew"
[ ! -f "$GCLOUD" ] && GCLOUD="$HOME/google-cloud-sdk/bin/gcloud"

GCP_VM="gitlab-runner"
GCP_ZONE="europe-west3-a"

case "$1" in
  mac)
    echo "🍎 Aktiviere Mac Runner..."
    $BREW services start gitlab-runner
    echo "☁️  Stoppe GCP Runner..."
    $GCLOUD compute instances stop $GCP_VM --zone=$GCP_ZONE --quiet
    echo "✅ Mac aktiv, GCP gestoppt"
    ;;
    
  gcp)
    echo "🍎 Stoppe Mac Runner..."
    $BREW services stop gitlab-runner
    echo "☁️  Starte GCP Runner..."
    $GCLOUD compute instances start $GCP_VM --zone=$GCP_ZONE --quiet
    echo "⏳ Warte auf GCP Boot (30s)..."
    sleep 30
    echo "✅ GCP aktiv, Mac gestoppt"
    ;;
    
  status)
    echo "═══════════════════════════════════════════════════════════"
    echo "  🏃 RUNNER STATUS"
    echo "═══════════════════════════════════════════════════════════"
    echo ""
    echo -n "🍎 Mac:  "
    $BREW services list | grep gitlab-runner | awk '{print $2}'
    echo -n "☁️  GCP:  "
    $GCLOUD compute instances describe $GCP_VM --zone=$GCP_ZONE --format='value(status)' 2>/dev/null || echo "NICHT GEFUNDEN"
    echo ""
    ;;
    
  auto)
    MAC_STATUS=$($BREW services list | grep gitlab-runner | awk '{print $2}')
    
    if [ "$MAC_STATUS" = "started" ]; then
      echo "🍎 Mac läuft → GCP nicht nötig"
      GCP_STATUS=$($GCLOUD compute instances describe $GCP_VM --zone=$GCP_ZONE --format='value(status)' 2>/dev/null)
      if [ "$GCP_STATUS" = "RUNNING" ]; then
        echo "☁️  GCP läuft auch → stoppe zur Kostenersparnis"
        $GCLOUD compute instances stop $GCP_VM --zone=$GCP_ZONE --quiet
      fi
    else
      echo "🍎 Mac nicht aktiv → starte GCP"
      $GCLOUD compute instances start $GCP_VM --zone=$GCP_ZONE --quiet
    fi
    ;;
    
  *)
    echo "Usage: $0 {mac|gcp|status|auto}"
    echo ""
    echo "  mac    - Mac an, GCP aus"
    echo "  gcp    - GCP an, Mac aus"
    echo "  status - Zeigt Status"
    echo "  auto   - Mac bevorzugt, GCP als Fallback"
    exit 1
    ;;
esac
