# This file defines the DynamoDB table used to store the "to-dos" for the application.

resource "aws_dynamodb_table" "to_dos" {
  name         = "${local.name_prefix}-to_dos"
  billing_mode = "PAY_PER_REQUEST"

  # Primary key for the table
  hash_key = "id"

  attribute {
    name = "id"
    type = "S"
  }

  # GSI keys to support dedupe lookup: "open ticket by repo"
  attribute {
    name = "repo"
    type = "S"
  }

  attribute {
    name = "status"
    type = "S"
  }

  global_secondary_index {
    name            = "gsi_repo_status"
    hash_key        = "repo"
    range_key       = "status"
    projection_type = "ALL"
  }

  tags = local.tags
}
