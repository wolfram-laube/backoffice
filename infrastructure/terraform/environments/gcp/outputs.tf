# ══════════════════════════════════════════════════════════════
# Outputs
# ══════════════════════════════════════════════════════════════

output "project_id" {
  description = "GCP Project ID"
  value       = data.google_project.current.project_id
}

output "project_number" {
  description = "GCP Project Number"
  value       = data.google_project.current.number
}

# TODO: Add outputs for resources when created:
# output "cloud_run_url" {
#   description = "CLARISSA API URL"
#   value       = google_cloud_run_service.api.status[0].url
# }
