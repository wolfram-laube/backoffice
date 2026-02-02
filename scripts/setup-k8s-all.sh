#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# BLAUWEISS K8S SETUP - All-in-One
# ═══════════════════════════════════════════════════════════════
# 
# Dieses Script:
#   1. Startet GCP VM
#   2. Installiert k3s auf GCP
#   3. Konfiguriert kubeconfig (Mac + GCP)
#   4. Deployed Timesheet App auf beide Cluster
#   5. Erstellt GitLab Secret
#
# ═══════════════════════════════════════════════════════════════

set -e

GCP_VM="gitlab-runner"
GCP_ZONE="europe-west3-a"
GCP_PROJECT="myk8sproject-207017"
GITLAB_PROJECT_ID="77555895"

K8S_MAC_CONTEXT="docker-desktop"
K8S_GCP_CONTEXT="k3s-gcp"

echo "═══════════════════════════════════════════════════════════"
echo "  ☸️  BLAUWEISS K8S SETUP"
echo "═══════════════════════════════════════════════════════════"
echo ""

# ─────────────────────────────────────────────────────────────────
# 1. GCP VM starten
# ─────────────────────────────────────────────────────────────────
echo "☁️  [1/6] GCP VM starten..."
VM_STATUS=$(gcloud compute instances describe $GCP_VM --zone=$GCP_ZONE --project=$GCP_PROJECT --format='get(status)' 2>/dev/null || echo "UNKNOWN")

if [ "$VM_STATUS" != "RUNNING" ]; then
    gcloud compute instances start $GCP_VM --zone=$GCP_ZONE --project=$GCP_PROJECT --quiet
    echo "    ⏳ Warte auf Boot (60s)..."
    sleep 60
else
    echo "    ✅ VM läuft bereits"
fi

EXTERNAL_IP=$(gcloud compute instances describe $GCP_VM --zone=$GCP_ZONE --project=$GCP_PROJECT --format='get(networkInterfaces[0].accessConfigs[0].natIP)')
echo "    🌐 IP: $EXTERNAL_IP"

# ─────────────────────────────────────────────────────────────────
# 2. k3s auf GCP installieren
# ─────────────────────────────────────────────────────────────────
echo ""
echo "☸️  [2/6] k3s auf GCP installieren..."

gcloud compute ssh $GCP_VM --zone=$GCP_ZONE --project=$GCP_PROJECT --command="
    if command -v k3s &> /dev/null; then
        echo '    ✅ k3s bereits installiert'
        kubectl get nodes
    else
        echo '    📦 Installiere k3s...'
        curl -sfL https://get.k3s.io | sh -s - \
            --write-kubeconfig-mode 644 \
            --disable traefik \
            --disable servicelb \
            --tls-san $EXTERNAL_IP
        
        # Warte auf k3s
        sleep 15
        
        # kubeconfig setup
        mkdir -p ~/.kube
        sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
        sudo chown \$(id -u):\$(id -g) ~/.kube/config
        
        # Ingress-Nginx
        echo '    🌐 Installiere Ingress-Nginx...'
        kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.9.4/deploy/static/provider/baremetal/deploy.yaml
        
        # Namespace
        kubectl create namespace blauweiss --dry-run=client -o yaml | kubectl apply -f -
        
        echo '    ✅ k3s installiert'
        kubectl get nodes
    fi
"

# ─────────────────────────────────────────────────────────────────
# 3. Firewall (falls nicht existiert)
# ─────────────────────────────────────────────────────────────────
echo ""
echo "🔥 [3/6] Firewall konfigurieren..."

if ! gcloud compute firewall-rules describe allow-k8s-http --project=$GCP_PROJECT &>/dev/null; then
    gcloud compute firewall-rules create allow-k8s-http \
        --project=$GCP_PROJECT \
        --allow tcp:80,tcp:443,tcp:6443,tcp:30080,tcp:30443 \
        --source-ranges=0.0.0.0/0 \
        --description="K8s Ingress + API" \
        --quiet
    echo "    ✅ Firewall Rule erstellt"
else
    echo "    ✅ Firewall Rule existiert"
fi

# ─────────────────────────────────────────────────────────────────
# 4. Kubeconfig mergen
# ─────────────────────────────────────────────────────────────────
echo ""
echo "📋 [4/6] Kubeconfig konfigurieren..."

# GCP kubeconfig holen
gcloud compute ssh $GCP_VM --zone=$GCP_ZONE --project=$GCP_PROJECT --command="cat ~/.kube/config" > /tmp/k3s-config.yaml

# IP + Context anpassen
sed -i '' "s/127.0.0.1/$EXTERNAL_IP/g" /tmp/k3s-config.yaml
sed -i '' "s/name: default/name: $K8S_GCP_CONTEXT/g" /tmp/k3s-config.yaml
sed -i '' "s/cluster: default/cluster: $K8S_GCP_CONTEXT/g" /tmp/k3s-config.yaml
sed -i '' "s/user: default/user: $K8S_GCP_CONTEXT/g" /tmp/k3s-config.yaml
sed -i '' "s/current-context: default/current-context: $K8S_GCP_CONTEXT/g" /tmp/k3s-config.yaml

# Backup
cp ~/.kube/config ~/.kube/config.backup.$(date +%Y%m%d%H%M%S) 2>/dev/null || true

# Merge (nur wenn k3s-gcp noch nicht existiert)
if ! kubectl config get-contexts $K8S_GCP_CONTEXT &>/dev/null; then
    KUBECONFIG=~/.kube/config:/tmp/k3s-config.yaml kubectl config view --flatten > ~/.kube/config.merged
    mv ~/.kube/config.merged ~/.kube/config
    echo "    ✅ Context '$K8S_GCP_CONTEXT' hinzugefügt"
else
    echo "    ✅ Context '$K8S_GCP_CONTEXT' existiert"
fi

echo ""
echo "    📋 Verfügbare Contexts:"
kubectl config get-contexts

# ─────────────────────────────────────────────────────────────────
# 5. GitLab Token eingeben
# ─────────────────────────────────────────────────────────────────
echo ""
echo "🔑 [5/6] GitLab Token als K8s Secret..."

# Token abfragen falls nicht gesetzt
if [ -z "$GITLAB_TOKEN" ]; then
    echo "    Bitte GitLab PAT eingeben (wird nicht angezeigt):"
    read -s GITLAB_TOKEN
fi

# Secret auf beiden Clustern erstellen
for CTX in "$K8S_MAC_CONTEXT" "$K8S_GCP_CONTEXT"; do
    echo "    → $CTX"
    kubectl config use-context $CTX &>/dev/null || continue
    kubectl create namespace blauweiss --dry-run=client -o yaml | kubectl apply -f - &>/dev/null
    kubectl create secret generic gitlab-credentials \
        --namespace=blauweiss \
        --from-literal=GITLAB_TOKEN="$GITLAB_TOKEN" \
        --from-literal=GITLAB_PROJECT_ID="$GITLAB_PROJECT_ID" \
        --dry-run=client -o yaml | kubectl apply -f -
done
echo "    ✅ Secrets erstellt"

# ─────────────────────────────────────────────────────────────────
# 6. Manifests deployen
# ─────────────────────────────────────────────────────────────────
echo ""
echo "🚀 [6/6] Manifests deployen..."

MANIFEST_BASE="https://gitlab.com/wolfram_laube/blauweiss_llc/ops/backoffice/-/raw/main/infra/k8s"

for CTX in "$K8S_MAC_CONTEXT" "$K8S_GCP_CONTEXT"; do
    echo "    → $CTX"
    kubectl config use-context $CTX &>/dev/null || continue
    
    kubectl apply -f "$MANIFEST_BASE/00-namespace.yaml" &>/dev/null
    kubectl apply -f "$MANIFEST_BASE/10-timesheet-backend.yaml" &>/dev/null
    kubectl apply -f "$MANIFEST_BASE/11-timesheet-frontend.yaml" &>/dev/null
    kubectl apply -f "$MANIFEST_BASE/20-ingress.yaml" &>/dev/null
done
echo "    ✅ Deployed"

# ─────────────────────────────────────────────────────────────────
# Fertig!
# ─────────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  ✅ SETUP COMPLETE!"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "  🍎 Mac:  kubectl config use-context $K8S_MAC_CONTEXT"
echo "  ☁️  GCP:  kubectl config use-context $K8S_GCP_CONTEXT"
echo ""
echo "  🌐 Timesheet App:"
echo "     Mac: http://localhost (wenn Ingress aktiv)"
echo "     GCP: http://$EXTERNAL_IP:30080"
echo ""
echo "  🔄 Flip-Flop:"
echo "     ./scripts/runner-flip-k8s.sh mac"
echo "     ./scripts/runner-flip-k8s.sh gcp"
echo "     ./scripts/runner-flip-k8s.sh status"
echo ""
