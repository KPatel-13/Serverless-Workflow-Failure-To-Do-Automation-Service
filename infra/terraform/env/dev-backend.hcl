# Remote backend settings for the dev environment.
#
# Why:
# - Stores dev Terraform state in S3 so local runs and GitHub Actions share it.
# - Uses a dedicated state key for dev so it stays separate from prod.
# - Uses S3 lockfiles for state locking.

bucket       = "dev-backend-bucket-bbgetc"
key          = "serverless-workflow-failure-to-do/dev/terraform.tfstate"
region       = "eu-west-2"
encrypt      = true
use_lockfile = true