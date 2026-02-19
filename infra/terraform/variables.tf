# Declares input variables so the same code can be reused across dev and prod environments + stops any hardcoding of values.

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
  description = "Shared secret required by POST /workflow-failure (set per environment). Leave empty for early dev."
  type        = string
  sensitive   = true
  default     = ""
}
