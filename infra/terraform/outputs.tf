# Defines values Terraform should print after applying changes:
#    - useful for outputs like resource ARNs or URLs that are needed for later steps in the project.

output "name_prefix" {
  description = "Name prefix used for all resources"
  value       = local.name_prefix
}

output "aws_region" {
  description = "AWS region resources are deployed into"
  value       = var.aws_region
}

output "dynamodb_table_name" {
  description = "DynamoDB table used to store tickets"
  value       = aws_dynamodb_table.todos.name
}

output "lambda_function_name" {
  description = "Lambda function that handles the API"
  value       = aws_lambda_function.api.function_name
}

output "http_api_endpoint" {
  description = "Base URL for the HTTP API"
  value       = aws_apigatewayv2_api.api.api_endpoint
}
