# Pins the minimum Terraform version and the provider the project depends on (AWS).#

terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.34.0"
    }

    # archive provider is used by data "archive_file" (Lambda zip packaging)
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.7.1"
    }

    null = {
      source  = "hashicorp/null"
      version = "~> 3.2.4"
    }
  }
}
