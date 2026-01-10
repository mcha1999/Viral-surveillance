# Viral Weather - Terraform Variables

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}

variable "app_name" {
  description = "Application name (used for resource naming)"
  type        = string
  default     = "viral-weather"
}

variable "environment" {
  description = "Environment (development, staging, production)"
  type        = string
  default     = "development"

  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be development, staging, or production."
  }
}

# Database
variable "db_tier" {
  description = "Cloud SQL machine tier"
  type        = string
  default     = "db-f1-micro" # Cost-optimized for MVP, upgrade to db-custom-2-8192 for production
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "viral_weather"
}

variable "db_user" {
  description = "Database user"
  type        = string
  default     = "viral_weather_app"
}

variable "db_password" {
  description = "Database password"
  type        = string
  sensitive   = true
}

# API Keys (set via environment or tfvars)
variable "aviationstack_api_key" {
  description = "AviationStack API key"
  type        = string
  sensitive   = true
  default     = ""
}

variable "mapbox_token" {
  description = "Mapbox access token"
  type        = string
  sensitive   = true
  default     = ""
}
