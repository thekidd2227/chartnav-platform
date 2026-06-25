provider "aws" {
  region = var.aws_region

  default_tags {
    tags = local.common_tags
  }
}

# CloudFront + ACM for CloudFront require us-east-1 certificates.
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"

  default_tags {
    tags = local.common_tags
  }
}
