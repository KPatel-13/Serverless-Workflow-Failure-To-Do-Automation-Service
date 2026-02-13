# API Gateway (HTTP API)

resource "aws_apigatewayv2_api" "api" {
  name          = "${local.name_prefix}-api"
  protocol_type = "HTTP"

  # CORS so the browser-based UI can call the API
  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["GET", "POST", "PATCH", "OPTIONS"]
    allow_headers = ["content-type", "x-workflow-secret"]
  }

  tags = local.tags
}

# Integration: API -> Lambda

resource "aws_apigatewayv2_integration" "api_to_lambda" {
  api_id                 = aws_apigatewayv2_api.api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.api.arn
  payload_format_version = "2.0"
}

# Routes

resource "aws_apigatewayv2_route" "route_workflow_failure" {
  api_id    = aws_apigatewayv2_api.api.id
  route_key = "POST /workflow-failure"
  target    = "integrations/${aws_apigatewayv2_integration.api_to_lambda.id}"
}

resource "aws_apigatewayv2_route" "route_list_todos" {
  api_id    = aws_apigatewayv2_api.api.id
  route_key = "GET /todos"
  target    = "integrations/${aws_apigatewayv2_integration.api_to_lambda.id}"
}

resource "aws_apigatewayv2_route" "route_patch_todo" {
  api_id    = aws_apigatewayv2_api.api.id
  route_key = "PATCH /todos/{id}"
  target    = "integrations/${aws_apigatewayv2_integration.api_to_lambda.id}"
}

# Stage (deployment)

resource "aws_apigatewayv2_stage" "default_stage" {
  api_id      = aws_apigatewayv2_api.api.id
  name        = "$default"
  auto_deploy = true

  tags = local.tags
}


# Permission: allow API Gateway to call Lambda

resource "aws_lambda_permission" "apigw_invoke_lambda" {
  statement_id  = "AllowInvokeFromApiGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"

  # Any method/route from this API can invoke the Lambda
  source_arn = "${aws_apigatewayv2_api.api.execution_arn}/*/*"
}
