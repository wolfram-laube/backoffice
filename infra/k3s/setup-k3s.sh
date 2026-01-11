#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# k3s Setup für Blauweiss Admin Portal
# GCP VM: gitlab-runner
# ═══════════════════════════════════════════════════════════════

set -e

echo "🚀 k3s Installation startet..."
echo "════════════════════════════════════════════════════════"

# System Update
echo "📦 System Update..."
sudo apt-get update -qq
sudo apt-get install -y -qq curl wget git jq

# k3s installieren (ohne Traefik, wir nutzen nginx-ingress)
echo "☸️ k3s installieren..."
curl -sfL https://get.k3s.io | sh -s - \
    --write-kubeconfig-mode 644 \
    --disable traefik \
    --disable servicelb \
    --tls-san $(curl -s ifconfig.me)

# Warte auf k3s
echo "⏳ Warte auf k3s..."
for i in {1..30}; do
    if sudo kubectl get nodes &>/dev/null; then
        break
    fi
    sleep 2
done

# kubectl ohne sudo
mkdir -p ~/.kube
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown $(id -u):$(id -g) ~/.kube/config
export KUBECONFIG=~/.kube/config

# Ingress-Nginx installieren
echo "🌐 Ingress-Nginx installieren..."
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.9.4/deploy/static/provider/baremetal/deploy.yaml

# Warte auf Ingress
echo "⏳ Warte auf Ingress Controller..."
kubectl wait --namespace ingress-nginx \
    --for=condition=ready pod \
    --selector=app.kubernetes.io/component=controller \
    --timeout=120s 2>/dev/null || echo "Ingress starting..."

# NodePort für HTTP/HTTPS patchen (80/443 direkt)
kubectl patch svc ingress-nginx-controller -n ingress-nginx --type='json' -p='[
  {"op": "replace", "path": "/spec/type", "value": "NodePort"},
  {"op": "replace", "path": "/spec/ports/0/nodePort", "value": 30080},
  {"op": "replace", "path": "/spec/ports/1/nodePort", "value": 30443}
]' 2>/dev/null || true

# Namespace blauweiss
echo "📁 Namespace erstellen..."
kubectl create namespace blauweiss --dry-run=client -o yaml | kubectl apply -f -

# External IP
EXTERNAL_IP=$(curl -s ifconfig.me)

echo ""
echo "════════════════════════════════════════════════════════"
echo "✅ k3s Installation abgeschlossen!"
echo "════════════════════════════════════════════════════════"
echo ""
kubectl get nodes
echo ""
echo "🌐 External IP: $EXTERNAL_IP"
echo "📋 Kubeconfig: ~/.kube/config"
echo ""
echo "🔧 Für Mac-Zugriff, kopiere kubeconfig:"
echo "   cat ~/.kube/config | sed 's/127.0.0.1/$EXTERNAL_IP/'"
