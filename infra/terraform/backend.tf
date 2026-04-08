# Shared remote backend declaration.
#This keeps dev and prod state separate without duplicating the Terraform codebase.

terraform {
  backend "s3" {}
}