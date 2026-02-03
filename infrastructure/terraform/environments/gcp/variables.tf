# ══════════════════════════════════════════════════════════════
# Input Variables
# ══════════════════════════════════════════════════════════════

variable "gcp_project" {
  description = "GCP Project ID"
  type        = string
  default     = "blauweiss-llc" # Default for CI validation
}

variable "gcp_region" {
  description = "GCP Region"
  type        = string
  default     = "europe-north1" # Stockholm - cheapest EU region
}

variable "gcp_zone" {
  description = "GCP Zone"
  type        = string
  default     = "europe-north1-a"
}

# ══════════════════════════════════════════════════════════════
# API Keys (from CI variables)
# ══════════════════════════════════════════════════════════════

variable "openai_api_key" {
  description = "OpenAI API Key for CLARISSA"
  type        = string
  sensitive   = true
  default     = ""
}

variable "anthropic_api_key" {
  description = "Anthropic API Key for CLARISSA"
  type        = string
  sensitive   = true
  default     = ""
}

variable "gitlab_deploy_token" {
  description = "GitLab Deploy Token for container registry"
  type        = string
  sensitive   = true
  default     = ""
}
