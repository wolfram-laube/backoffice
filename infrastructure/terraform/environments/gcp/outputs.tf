# ══════════════════════════════════════════════════════════════
# Outputs
# ══════════════════════════════════════════════════════════════

output "gcp_project" {
  description = "GCP Project ID"
  value       = var.gcp_project
}

output "gcp_region" {
  description = "GCP Region"
  value       = var.gcp_region
}

# TODO: Add outputs for resources when created:
# output "cloud_run_url" {
#   description = "CLARISSA API URL"
#   value       = google_cloud_run_service.api.status[0].url
# }
