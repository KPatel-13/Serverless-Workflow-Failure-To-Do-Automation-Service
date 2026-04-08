# Variables for the Terraform backend bootstrap stack.
#
# Why:
# - This stack creates the remote state buckets needed by the main Terraform stack.
# - We use one map so the same resource definitions can create both dev and prod buckets
#   without repeating the code.

variable "backend_buckets" {
  description = "Map of backend bucket names by environment"
  type = map(string)
}