# Outputs the created backend bucket names by environment.

output "backend_bucket_names" {
  description = "Terraform backend bucket names by environment"
  value = {
    for env, bucket in aws_s3_bucket.terraform_state : env => bucket.bucket
  }
}