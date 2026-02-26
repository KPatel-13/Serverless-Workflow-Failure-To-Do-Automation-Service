# Configures the provider (AWS) with settings like region - will help stop any repetition.

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = local.tags
  }
}
