# Storage Configuration

## GCP Cloud Storage (S3-compatible)

1. Go to GCP Console → Cloud Storage → Settings → Interoperability
2. Create HMAC Key
3. Save as gcs-hmac.json:

```json
{
  "access_key": "GOOG...",
  "secret_key": "...",
  "endpoint": "https://storage.googleapis.com",
  "bucket": "your-bucket-name"
}
```

## rclone

Configure with: rclone config

For GDrive:
```
[gdrive]
type = drive
scope = drive
token = {...}
```

Save as rclone.conf
