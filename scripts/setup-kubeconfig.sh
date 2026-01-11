#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# Kubeconfig Setup: Mac + GCP k3s
# ═══════════════════════════════════════════════════════════════

GCP_VM="gitlab-runner"
GCP_ZONE="europe-west3-a"
K3S_CONTEXT="k3s-gcp"

echo "☸️ Kubeconfig Setup"
echo "════════════════════════════════════════════════════════"

# 1. GCP k3s kubeconfig holen
echo "📥 Hole k3s kubeconfig von GCP..."
gcloud compute ssh $GCP_VM --zone=$GCP_ZONE --command="cat ~/.kube/config" > /tmp/k3s-config.yaml

# 2. External IP holen
EXTERNAL_IP=$(gcloud compute instances describe $GCP_VM --zone=$GCP_ZONE --format='get(networkInterfaces[0].accessConfigs[0].natIP)')
echo "🌐 GCP IP: $EXTERNAL_IP"

# 3. IP ersetzen
sed -i '' "s/127.0.0.1/$EXTERNAL_IP/" /tmp/k3s-config.yaml

# 4. Context umbenennen
sed -i '' "s/name: default/name: $K3S_CONTEXT/" /tmp/k3s-config.yaml
sed -i '' "s/cluster: default/cluster: $K3S_CONTEXT/" /tmp/k3s-config.yaml
sed -i '' "s/user: default/user: $K3S_CONTEXT/" /tmp/k3s-config.yaml
sed -i '' "s/current-context: default/current-context: $K3S_CONTEXT/" /tmp/k3s-config.yaml

# 5. Backup bestehende config
cp ~/.kube/config ~/.kube/config.backup.$(date +%Y%m%d%H%M%S)

# 6. Configs mergen
echo "🔀 Merge kubeconfigs..."
KUBECONFIG=~/.kube/config:/tmp/k3s-config.yaml kubectl config view --flatten > ~/.kube/config.merged
mv ~/.kube/config.merged ~/.kube/config

echo ""
echo "════════════════════════════════════════════════════════"
echo "✅ Kubeconfig Setup abgeschlossen!"
echo "════════════════════════════════════════════════════════"
echo ""
echo "📋 Verfügbare Contexts:"
kubectl config get-contexts
echo ""
echo "🔧 Verwendung:"
echo "   kubectl config use-context docker-desktop  # Mac lokal"
echo "   kubectl config use-context $K3S_CONTEXT    # GCP k3s"
