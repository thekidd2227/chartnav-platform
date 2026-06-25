# Customer-managed KMS keys (one per data domain) with rotation enabled.

resource "aws_kms_key" "rds" {
  description             = "${local.name} RDS encryption"
  enable_key_rotation     = true
  deletion_window_in_days = 30
  tags                    = { Name = "${local.name}-rds" }
}

resource "aws_kms_alias" "rds" {
  name          = "alias/${local.name}-rds"
  target_key_id = aws_kms_key.rds.key_id
}

resource "aws_kms_key" "s3" {
  description             = "${local.name} S3 object encryption"
  enable_key_rotation     = true
  deletion_window_in_days = 30
  tags                    = { Name = "${local.name}-s3" }
}

resource "aws_kms_alias" "s3" {
  name          = "alias/${local.name}-s3"
  target_key_id = aws_kms_key.s3.key_id
}

resource "aws_kms_key" "secrets" {
  description             = "${local.name} Secrets Manager encryption"
  enable_key_rotation     = true
  deletion_window_in_days = 30
  tags                    = { Name = "${local.name}-secrets" }
}

resource "aws_kms_alias" "secrets" {
  name          = "alias/${local.name}-secrets"
  target_key_id = aws_kms_key.secrets.key_id
}

resource "aws_kms_key" "logs" {
  description             = "${local.name} CloudWatch Logs encryption"
  enable_key_rotation     = true
  deletion_window_in_days = 30
  policy                  = data.aws_iam_policy_document.logs_kms.json
  tags                    = { Name = "${local.name}-logs" }
}

resource "aws_kms_alias" "logs" {
  name          = "alias/${local.name}-logs"
  target_key_id = aws_kms_key.logs.key_id
}

data "aws_caller_identity" "current" {}

# CloudWatch Logs needs explicit permission to use the CMK.
data "aws_iam_policy_document" "logs_kms" {
  statement {
    sid       = "EnableRoot"
    actions   = ["kms:*"]
    resources = ["*"]
    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"]
    }
  }
  statement {
    sid     = "AllowCloudWatchLogs"
    actions = ["kms:Encrypt*", "kms:Decrypt*", "kms:ReEncrypt*", "kms:GenerateDataKey*", "kms:Describe*"]
    resources = ["*"]
    principals {
      type        = "Service"
      identifiers = ["logs.${var.aws_region}.amazonaws.com"]
    }
  }
}
