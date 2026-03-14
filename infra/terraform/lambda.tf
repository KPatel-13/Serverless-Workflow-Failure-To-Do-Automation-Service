# Packages Lambda code into a zip that AWS Lambda can run.

# Ensure build directory exists so archive_file can write output_path reliably
resource "aws_iam_role" "lambda_role" {
  name = "${local.name_prefix}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect    = "Allow",
      Principal = { Service = "lambda.amazonaws.com" },
      Action    = "sts:AssumeRole"
    }]
  })
  tags = local.tags
}

# AWS-managed basic logging policy for CloudWatch Logs.
resource "aws_iam_role_policy_attachment" "lambda_basic_logs" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Explicit log group with retention.
#
# Why:
# - Gives predictable retention for cost control
# - Helps satisfy minimal observability requirements
resource "aws_cloudwatch_log_group" "lambda_log_group" {
  name              = "/aws/lambda/${local.name_prefix}-api"
  retention_in_days = 14
  tags              = local.tags
}

# IAM role that Lambda assumes when it runs
# Custom IAM policy for DynamoDB access.
#
# Why these actions:
# - GetItem: direct lookup by id
# - PutItem: insert/update whole ticket
# - UpdateItem: kept because your design may evolve to partial updates
# - Query: needed for GSI-based querying
# - Scan: needed for GET /todos listing
resource "aws_iam_policy" "lambda_dynamodb_policy" {
  name = "${local.name_prefix}-lambda-dynamodb"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Action = [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:Query",
        "dynamodb:Scan"
      ],
      Resource = [
        # Base table ARN
        aws_dynamodb_table.todos.arn,
        # Allow access to indexes on this table, including gsi_repo_fingerprint
        "${aws_dynamodb_table.todos.arn}/index/*"
      ]
    }]
  })

  tags = local.tags
}

resource "aws_iam_role_policy_attachment" "lambda_dynamodb_attach" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.lambda_dynamodb_policy.arn
}

# Lambda function resource.
#
# Why the handler changed:
# - zip contains app/handler.py
# - So Lambda must use app.handler.lambda_handler
#
# Why filename points to lambda.zip:
# - We use the packaging script as the single build mechanism
# - Terraform's job becomes deployment, not packaging
resource "aws_lambda_function" "api" {
  function_name = "${local.name_prefix}-api"
  role          = aws_iam_role.lambda_role.arn
#name of the handler function within the code with the format file_name.function_name.
  handler = "app.handler.lambda_handler"
  runtime = "python3.11"

  timeout     = 10
  memory_size = 256

  filename         = "${path.module}/../../lambda.zip"
  source_code_hash = filebase64sha256("${path.module}/../../lambda.zip")
# env variables for the lambda function, including the DynamoDB table name and workflow secret
  environment {
    variables = {
      # Tells handler.py to use DynamoDBRepository in AWS
      TODOS_TABLE = aws_dynamodb_table.todos.name

      # Shared secret required by POST /workflow-failure
      WORKFLOW_SECRET = var.workflow_secret

      # Basic structured logging level
      LOG_LEVEL = "INFO"
    }
  }

  # Ensure the log group exists before the function is first invoked.
  depends_on = [aws_cloudwatch_log_group.lambda_log_group]

  tags = local.tags
}
