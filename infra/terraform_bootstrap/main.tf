# Creates the S3 buckets used for Terraform remote state.
#
# Why this is separate from the main Terraform stack:
# - The remote backend buckets must already exist before the main stack can use them.
# - This avoids the bootstrap/chicken-and-egg problem.
#
# Why use for_each:
# - Lets us create both dev and prod backend buckets from one shared definition.
# - Keeps the code DRY while still giving each environment its own bucket.

resource "aws_s3_bucket" "terraform_state" {
  for_each = var.backend_buckets

  bucket = each.value

  tags = {
    Project     = "workflow-failure-to-do"
    ManagedBy   = "terraform"
    Purpose     = "terraform-backend"
    Environment = each.key
  }
}

# Enable bucket versioning for safer state recovery.
# HashiCorp strongly recommends versioning on backend buckets.
resource "aws_s3_bucket_versioning" "terraform_state_versioning" {
  for_each = aws_s3_bucket.terraform_state

  bucket = each.value.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Enable default server-side encryption for backend state objects.
resource "aws_s3_bucket_server_side_encryption_configuration" "terraform_state_encryption" {
  for_each = aws_s3_bucket.terraform_state

  bucket = each.value.bucket

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Block all public access as a safe default.
resource "aws_s3_bucket_public_access_block" "terraform_state_public_access" {
  for_each = aws_s3_bucket.terraform_state

  bucket = each.value.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}