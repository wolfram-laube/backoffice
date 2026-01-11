#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# Runner + K8s Flip-Flop: Mac ↔ GCP
# ═══════════════════════════════════════════════════════════════
# 
# Steuert:
#   - GitLab Runner (Mac homebrew ↔ GCP systemd)
#   - Kubernetes Context (docker-desktop ↔ k3s-gcp)
#   - GCP VM (start/stop)
#
# Usage:
#   ./runner-flip-k8s.sh mac      # Aktiviere Mac, stoppe GCP
#   ./runner-flip-k8s.sh gcp      # Aktiviere GCP, stoppe Mac
#   ./runner-flip-k8s.sh status   # Zeige Status
#   ./runner-flip-k8s.sh auto     # Auto-detect (für sleep/wake)
#
# ═══════════════════════════════════════════════════════════════

# Full paths for launchd/sleepwatcher compatibility
BREW="/usr/local/bin/brew"
GCLOUD="/usr/local/bin/gcloud"
KUBECTL="/usr/local/bin/kubectl"

# Fallback paths
[ ! -f "$BREW" ] && BREW="/opt/homebrew/bin/brew"
[ ! -f "$GCLOUD" ] && GCLOUD="$HOME/google-cloud-sdk/bin/gcloud"
[ ! -f "$KUBECTL" ] && KUBECTL="/opt/homebrew/bin/kubectl"

GCP_VM="gitlab-runner"
GCP_ZONE="europe-west3-a"
GCP_PROJECT="myk8sproject-207017"

# K8s Contexts
K8S_MAC_CONTEXT="docker-desktop"
K8S_GCP_CONTEXT="k3s-gcp"

# ═══════════════════════════════════════════════════════════════

mac_runner_start() {
    echo "🍎 Starte Mac Runner..."
    $BREW services start gitlab-runner 2>/dev/null || true
}

mac_runner_stop() {
    echo "🍎 Stoppe Mac Runner..."
    $BREW services stop gitlab-runner 2>/dev/null || true
}

gcp_vm_start() {
    echo "☁️  Starte GCP VM..."
    $GCLOUD compute instances start $GCP_VM --zone=$GCP_ZONE --project=$GCP_PROJECT --quiet
}

gcp_vm_stop() {
    echo "☁️  Stoppe GCP VM..."
    $GCLOUD compute instances stop $GCP_VM --zone=$GCP_ZONE --project=$GCP_PROJECT --quiet
}

k8s_context_mac() {
    echo "☸️  K8s Context → Mac (docker-desktop)"
    $KUBECTL config use-context $K8S_MAC_CONTEXT 2>/dev/null || true
}

k8s_context_gcp() {
    echo "☸️  K8s Context → GCP (k3s)"
    $KUBECTL config use-context $K8S_GCP_CONTEXT 2>/dev/null || true
}

get_status() {
    echo "═══════════════════════════════════════════════════════════"
    echo "  🏃 RUNNER + K8S STATUS"
    echo "═══════════════════════════════════════════════════════════"
    echo ""
    
    # Mac Runner
    MAC_STATUS=$($BREW services list 2>/dev/null | grep gitlab-runner | awk '{print $2}')
    echo "🍎 Mac Runner:  ${MAC_STATUS:-unknown}"
    
    # GCP VM
    GCP_STATUS=$($GCLOUD compute instances describe $GCP_VM --zone=$GCP_ZONE --project=$GCP_PROJECT --format='get(status)' 2>/dev/null)
    echo "☁️  GCP VM:      ${GCP_STATUS:-unknown}"
    
    # K8s Context
    K8S_CTX=$($KUBECTL config current-context 2>/dev/null)
    echo "☸️  K8s Context: ${K8S_CTX:-none}"
    
    # K8s Cluster Status
    if [ "$K8S_CTX" = "$K8S_MAC_CONTEXT" ]; then
        NODES=$($KUBECTL get nodes --no-headers 2>/dev/null | wc -l | tr -d ' ')
        echo "   └── Nodes:   $NODES (Mac)"
    elif [ "$K8S_CTX" = "$K8S_GCP_CONTEXT" ]; then
        NODES=$($KUBECTL get nodes --no-headers 2>/dev/null | wc -l | tr -d ' ')
        echo "   └── Nodes:   $NODES (GCP)"
    fi
    echo ""
}

# ═══════════════════════════════════════════════════════════════

case "$1" in
    mac)
        echo "🔄 Aktiviere MAC, stoppe GCP..."
        mac_runner_start
        k8s_context_mac
        gcp_vm_stop &
        sleep 2
        echo "✅ Mac aktiv, GCP gestoppt"
        ;;
    
    gcp)
        echo "🔄 Aktiviere GCP, stoppe Mac..."
        mac_runner_stop
        gcp_vm_start
        echo "⏳ Warte auf GCP Boot (45s)..."
        sleep 45
        k8s_context_gcp
        echo "✅ GCP aktiv, Mac gestoppt"
        ;;
    
    status)
        get_status
        ;;
    
    auto)
        # Für automatische Sleep/Wake Detection
        # Wird von sleepwatcher aufgerufen
        if pgrep -x "caffeinate" > /dev/null || pmset -g assertions | grep -q "PreventUserIdleSystemSleep.*1"; then
            # Mac ist aktiv
            mac_runner_start
            k8s_context_mac
            gcp_vm_stop &
        else
            # Mac schläft (oder wird schlafen)
            mac_runner_stop
            gcp_vm_start &
            k8s_context_gcp
        fi
        ;;
    
    *)
        echo "Usage: $0 {mac|gcp|status|auto}"
        echo ""
        echo "  mac     - Aktiviere Mac Runner + K8s, stoppe GCP"
        echo "  gcp     - Aktiviere GCP Runner + K8s, stoppe Mac"
        echo "  status  - Zeige aktuellen Status"
        echo "  auto    - Auto-detect für Sleep/Wake"
        exit 1
        ;;
esac
