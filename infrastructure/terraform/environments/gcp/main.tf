# ══════════════════════════════════════════════════════════════
# Terraform Configuration - GCP Infrastructure
# ══════════════════════════════════════════════════════════════
#
# Minimal skeleton for CI validation (terraform validate/fmt)
# Full plan/apply requires GCP credentials with proper scopes
#
# Required CI Variables for plan/apply:
#   - GOOGLE_CREDENTIALS: GCP Service Account JSON key
#   - TF_VAR_gcp_project: GCP Project ID

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  # Backend configured dynamically by CI
}

provider "google" {
  project = var.gcp_project
  region  = var.gcp_region
}

# ══════════════════════════════════════════════════════════════
# Resources (TBD)
# ══════════════════════════════════════════════════════════════

# TODO: Add resources as needed:
# - google_cloud_run_service
# - google_storage_bucket
# - google_secret_manager_secret
