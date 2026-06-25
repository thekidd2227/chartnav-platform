# AWS Backup vault + plan covering RDS (in addition to RDS automated backups
# + PITR). The vault is KMS-encrypted; the plan runs daily with retention.

resource "aws_backup_vault" "this" {
  name        = "${local.name}-vault"
  kms_key_arn = aws_kms_key.rds.arn
  tags        = { Name = "${local.name}-vault" }
}

resource "aws_iam_role" "backup" {
  name               = "${local.name}-backup"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = "sts:AssumeRole"
      Principal = { Service = "backup.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "backup" {
  role       = aws_iam_role.backup.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSBackupServiceRolePolicyForBackup"
}

resource "aws_backup_plan" "this" {
  name = "${local.name}-plan"

  rule {
    rule_name         = "daily"
    target_vault_name = aws_backup_vault.this.name
    schedule          = "cron(0 6 * * ? *)"
    start_window      = 60
    completion_window = 180
    lifecycle {
      delete_after = var.environment == "production" ? 35 : 14
    }
  }

  tags = { Name = "${local.name}-plan" }
}

resource "aws_backup_selection" "rds" {
  name         = "${local.name}-rds"
  plan_id      = aws_backup_plan.this.id
  iam_role_arn = aws_iam_role.backup.arn
  resources    = [aws_db_instance.this.arn]
}
