# Packages your Lambda code into a zip that AWS Lambda can run.

# Ensure build directory exists so archive_file can write output_path reliably
resource "null_resource" "build_dir" {
  provisioner "local-exec" {
    command = "mkdir -p ${path.module}/.build"
  }
}

data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../app"
  output_path = "${path.module}/.build/lambda.zip"

  depends_on = [null_resource.build_dir]
}

# IAM role that Lambda assumes when it runs
resource "aws_iam_role" "lambda_role" {
  name = "${local.name_prefix}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Principal = { Service = "lambda.amazonaws.com" },
      Action = "sts:AssumeRole"
    }]
  })

  tags = local.tags
}

# CloudWatch Logs permissions for Lambda
resource "aws_iam_role_policy_attachment" "lambda_basic_logs" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Log group with retention so logs don't grow forever (cost control)
resource "aws_cloudwatch_log_group" "lambda_log_group" {
  name              = "/aws/lambda/${local.name_prefix}-api"
  retention_in_days = 14
  tags              = local.tags
}

# Minimal DynamoDB permissions - attached to Lambda's execution role so it can read/write the "todos" table.
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
        "dynamodb:Query"
        # Add "dynamodb:DeleteItem" later if you implement DELETE /todos/{id}
      ],
      Resource = [
        # Base table
        aws_dynamodb_table.todos.arn,
        # Allow querying any GSI/LSI on this table (incl. gsi_repo_fingerprint)
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

# The Lambda function itself
resource "aws_lambda_function" "api" {
  function_name = "${local.name_prefix}-api"
  role          = aws_iam_role.lambda_role.arn

  # handler.py contains lambda_handler() so this is: file.function
  handler = "handler.lambda_handler"
  runtime = "python3.11"

  timeout     = 10
  memory_size = 256

  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  # Environment variables used by handler.py
  environment {
    variables = {
      TODOS_TABLE = aws_dynamodb_table.todos.name

      # Sprint 1: can be blank; later injected via TF_VAR_workflow_secret / CI secrets
      WORKFLOW_SECRET = var.workflow_secret
    }
  }

  # Ensure log group exists before first invocation
  depends_on = [aws_cloudwatch_log_group.lambda_log_group]

  tags = local.tags
}
