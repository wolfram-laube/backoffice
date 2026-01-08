#!/bin/bash
# ══════════════════════════════════════════════════════════════
# Runner Flip-Flop: Mac ↔ GCP
# ══════════════════════════════════════════════════════════════
#
# Usage:
#   runner-flip mac    → Mac an, GCP aus
#   runner-flip gcp    → GCP an, Mac aus  
#   runner-flip status → Zeigt Status beider Runner
#   runner-flip auto   → Automatisch (Mac bevorzugt)
#
# ══════════════════════════════════════════════════════════════

GCP_VM="gitlab-runner"
GCP_ZONE="europe-west3-a"

case "$1" in
  mac)
    echo "🍎 Aktiviere Mac Runner..."
    brew services start gitlab-runner
    echo "☁️  Stoppe GCP Runner..."
    gcloud compute instances stop $GCP_VM --zone=$GCP_ZONE --quiet
    echo "✅ Mac aktiv, GCP gestoppt"
    ;;
    
  gcp)
    echo "🍎 Stoppe Mac Runner..."
    brew services stop gitlab-runner
    echo "☁️  Starte GCP Runner..."
    gcloud compute instances start $GCP_VM --zone=$GCP_ZONE --quiet
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
    brew services list | grep gitlab-runner | awk '{print $2}'
    echo -n "☁️  GCP:  "
    gcloud compute instances describe $GCP_VM --zone=$GCP_ZONE --format='value(status)' 2>/dev/null || echo "NICHT GEFUNDEN"
    echo ""
    ;;
    
  auto)
    # Check Mac Runner
    MAC_STATUS=$(brew services list | grep gitlab-runner | awk '{print $2}')
    
    if [ "$MAC_STATUS" = "started" ]; then
      echo "🍎 Mac läuft → GCP nicht nötig"
      GCP_STATUS=$(gcloud compute instances describe $GCP_VM --zone=$GCP_ZONE --format='value(status)' 2>/dev/null)
      if [ "$GCP_STATUS" = "RUNNING" ]; then
        echo "☁️  GCP läuft auch → stoppe zur Kostenersparnis"
        gcloud compute instances stop $GCP_VM --zone=$GCP_ZONE --quiet
      fi
    else
      echo "🍎 Mac nicht aktiv → starte GCP"
      gcloud compute instances start $GCP_VM --zone=$GCP_ZONE --quiet
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
