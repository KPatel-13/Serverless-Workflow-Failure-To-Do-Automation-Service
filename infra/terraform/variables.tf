# Declares input variables so the same code can be reused across environments
# and avoids hardcoding values.

variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "eu-west-2"
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "workflow-failure-to-do"
}

variable "environment" {
  description = "Environment name (e.g., dev, prod)"
  type        = string
  default     = "dev"
}

variable "workflow_secret" {
  description = "Shared secret required by POST /workflow-failure. Must be provided per environment."
  type        = string
  sensitive   = true

  validation {
    condition     = length(trimspace(var.workflow_secret)) > 0
    error_message = "workflow_secret must be provided and must not be empty."
  }
}
