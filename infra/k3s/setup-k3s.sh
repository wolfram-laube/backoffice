#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# k3s Setup für Blauweiss Admin Portal
# ═══════════════════════════════════════════════════════════════

set -e

echo "🚀 k3s Installation startet..."
echo "════════════════════════════════════════════════════════"

# 1. System Update
echo "📦 System Update..."
sudo apt-get update -qq
sudo apt-get install -y -qq curl wget git

# 2. k3s installieren
echo "☸️ k3s installieren..."
curl -sfL https://get.k3s.io | sh -s - \
    --write-kubeconfig-mode 644 \
    --disable traefik \
    --disable servicelb

# Warte auf k3s
echo "⏳ Warte auf k3s..."
sleep 10

# 3. kubectl alias
echo "export KUBECONFIG=/etc/rancher/k3s/k3s.yaml" >> ~/.bashrc
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml

# 4. Ingress-Nginx installieren
echo "🌐 Ingress-Nginx installieren..."
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.9.4/deploy/static/provider/cloud/deploy.yaml

# 5. Namespace erstellen
echo "📁 Namespace 'blauweiss' erstellen..."
kubectl create namespace blauweiss --dry-run=client -o yaml | kubectl apply -f -

# 6. Verifikation
echo ""
echo "════════════════════════════════════════════════════════"
echo "✅ k3s Installation abgeschlossen!"
echo "════════════════════════════════════════════════════════"
echo ""
kubectl get nodes
echo ""
kubectl get pods -A
echo ""
echo "📋 Kubeconfig für lokalen Zugriff:"
echo "   sudo cat /etc/rancher/k3s/k3s.yaml"
echo ""
echo "🔑 Ersetze 'server: https://127.0.0.1:6443' mit:"
echo "   server: https://$(curl -s ifconfig.me):6443"
