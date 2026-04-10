# Resources will be added in later steps (DynamoDB, Lambda, API Gateway)
# Resources are split into separate files by concern:

# - dynamodb.tf
# - lambda.tf
# - apigw.tf
# - outputs.tf

module "frontend_infra" {
  source = "./frontend_infra"

  project_name = var.project_name
  environment  = var.environment
}