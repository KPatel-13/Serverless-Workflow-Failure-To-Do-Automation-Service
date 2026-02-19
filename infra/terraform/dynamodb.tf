# This file defines the DynamoDB table used to store the "todos" for the application.

resource "aws_dynamodb_table" "todos" {
  name         = "${local.name_prefix}-todos"
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
    projection_type = "ALL"

    key_schema {
      attribute_name = "repo"
      key_type       = "HASH"
    }

    key_schema {
      attribute_name = "status"
      key_type       = "RANGE"
    }
  }

  tags = local.tags
}
