# Remote backend settings for the prod environment.
#
# Why:
# - Stores prod Terraform state separately from dev.
# - Keeps production state isolated so promotion does not mutate dev state.
# - Uses S3 lockfiles for state locking.

bucket       = "prod-backend-bucket"
key          = "serverless-workflow-failure-to-do/prod/terraform.tfstate"
region       = "eu-west-2"
encrypt      = true
use_lockfile = true