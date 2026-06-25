variable "project" {
  description = "Project name, used for tagging + resource name prefixes."
  type        = string
  default     = "chartnav"
}

variable "environment" {
  description = "Deployment environment (staging | production)."
  type        = string
  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "environment must be 'staging' or 'production'."
  }
}

variable "aws_region" {
  description = "Primary AWS region. No default — set per environment."
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block for the dedicated VPC."
  type        = string
  default     = "10.40.0.0/16"
}

variable "az_count" {
  description = "Number of Availability Zones to spread subnets across."
  type        = number
  default     = 2
}

# ── DNS / TLS ──────────────────────────────────────────────────────────
variable "route53_zone_id" {
  description = "Existing Route 53 hosted zone id for the apex domain."
  type        = string
}

variable "app_hostname" {
  description = "Frontend hostname, e.g. app.chartnavmd.com."
  type        = string
}

variable "api_hostname" {
  description = "API hostname, e.g. api.chartnavmd.com."
  type        = string
}

# ── Database ───────────────────────────────────────────────────────────
variable "db_instance_class" {
  type    = string
  default = "db.t4g.medium"
}

variable "db_allocated_storage" {
  type    = string
  default = "50"
}

variable "db_engine_version" {
  type    = string
  default = "16.4"
}

variable "db_multi_az" {
  description = "Multi-AZ for the RDS instance (recommended in production)."
  type        = bool
  default     = false
}

variable "db_deletion_protection" {
  type    = bool
  default = false
}

variable "db_backup_retention_days" {
  type    = number
  default = 14
}

# ── ECS / API service ──────────────────────────────────────────────────
variable "api_image" {
  description = "Full ECR image URI:tag for the FastAPI service."
  type        = string
}

variable "api_desired_count" {
  type    = number
  default = 2
}

variable "api_cpu" {
  type    = number
  default = 512
}

variable "api_memory" {
  type    = number
  default = 1024
}

# ── Observability ──────────────────────────────────────────────────────
variable "log_retention_days" {
  type    = number
  default = 365
}

variable "alarm_email" {
  description = "Email subscribed to the CloudWatch alarm SNS topic."
  type        = string
  default     = ""
}

# ── Application config (non-secret) injected into the task ──────────────
variable "app_environment_extra" {
  description = "Extra non-secret env vars for the API task."
  type        = map(string)
  default     = {}
}
