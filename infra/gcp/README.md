# Infrastructure as Code

## GCP GitLab Runner

```
infra/gcp/
├── cloud-init.yaml          # VM initialization on first boot
├── gcp-runner-bootstrap.sh  # Idempotent setup script (run anytime)
└── README.md
```

### Erstellen einer neuen VM

```bash
./scripts/setup-gcp-runner.sh <TOKEN> [PROJECT_ID]
```

Das Script:
1. Erstellt VM mit `cloud-init.yaml` (Packages + Docker)
2. Führt `bootstrap.sh` aus (GitLab Runner + Registration)

### VM reparieren/updaten

```bash
gcloud compute ssh gitlab-runner --zone=europe-west3-a
sudo /tmp/bootstrap.sh
```

Oder remote:
```bash
gcloud compute scp infra/gcp/gcp-runner-bootstrap.sh gitlab-runner:/tmp/ --zone=europe-west3-a
gcloud compute ssh gitlab-runner --zone=europe-west3-a --command="sudo bash /tmp/gcp-runner-bootstrap.sh"
```

### Konfiguration

Environment Variables:
- `GCP_PROJECT` - GCP Project ID
- `GCP_ZONE` - Zone (default: europe-west3-a)
- `GCP_MACHINE` - Machine type (default: e2-small)
- `VM_NAME` - VM name (default: gitlab-runner)

### Kosten

| Komponente | Kosten/Monat |
|------------|--------------|
| e2-small (running) | ~$13 |
| e2-small (stopped) | ~$0.80 |
| 20GB pd-standard | ~$0.80 |
