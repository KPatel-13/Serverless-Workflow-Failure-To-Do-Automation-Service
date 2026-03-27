# This file defines the DynamoDB table used to store the "todos" for the application.

# DynamoDB table used to store workflow failure tickets ("todos").
#
# Why this design:
# - Primary key "id" stores the ticket id (currently the fingerprint)
# - Extra attributes "repo" and "fingerprint" support future query patterns
# - GSI on (repo, fingerprint) gives us a richer model ahead of later sprints

resource "aws_dynamodb_table" "todos" {
  name         = "${local.name_prefix}-todos"
  billing_mode = "PAY_PER_REQUEST"

  # Primary key for the table
  hash_key = "id"

  attribute {
    name = "id"
    type = "S"
  }

  attribute {
    name = "repo"
    type = "S"
  }

  attribute {
    name = "fingerprint"
    type = "S"
  }

  # Query the open ticket for a specific failure quickly using repo + fingerprint.
  # (A repo+status index can't uniquely identify "same failure".)
  global_secondary_index {
    name            = "gsi_repo_fingerprint"
    projection_type = "ALL"

    key_schema {
      attribute_name = "repo"
      key_type       = "HASH"
    }

    key_schema {
      attribute_name = "fingerprint"
      key_type       = "RANGE"
    }
  }

  tags = local.tags
}