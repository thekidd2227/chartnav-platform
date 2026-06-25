terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.40"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # Remote state is configured per-environment via a backend config file:
  #   terraform init -backend-config=environments/<env>.backend.hcl
  # (S3 bucket + DynamoDB lock table created out-of-band, not by this stack).
  backend "s3" {}
}
