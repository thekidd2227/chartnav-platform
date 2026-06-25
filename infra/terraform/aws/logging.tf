# CloudWatch log groups (KMS-encrypted, configurable retention).

resource "aws_cloudwatch_log_group" "api" {
  name              = "/chartnav/${var.environment}/api"
  retention_in_days = var.log_retention_days
  kms_key_id        = aws_kms_key.logs.arn
  tags              = { Name = "${local.name}-api" }
}

resource "aws_cloudwatch_log_group" "migrate" {
  name              = "/chartnav/${var.environment}/migrate"
  retention_in_days = var.log_retention_days
  kms_key_id        = aws_kms_key.logs.arn
  tags              = { Name = "${local.name}-migrate" }
}
