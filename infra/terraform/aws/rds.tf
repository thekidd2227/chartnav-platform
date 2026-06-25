# Managed PostgreSQL — private only, encrypted, PITR, automated backups.

resource "aws_db_subnet_group" "this" {
  name       = "${local.name}-db"
  subnet_ids = aws_subnet.private[*].id
  tags       = { Name = "${local.name}-db" }
}

resource "aws_db_parameter_group" "this" {
  name   = "${local.name}-pg16"
  family = "postgres16"

  # Require TLS for all client connections.
  parameter {
    name  = "rds.force_ssl"
    value = "1"
  }

  tags = { Name = "${local.name}-pg16" }
}

resource "random_password" "db" {
  length  = 32
  special = false
}

resource "aws_db_instance" "this" {
  identifier     = "${local.name}-pg"
  engine         = "postgres"
  engine_version = var.db_engine_version
  instance_class = var.db_instance_class

  allocated_storage     = var.db_allocated_storage
  max_allocated_storage = var.db_allocated_storage * 4
  storage_type          = "gp3"
  storage_encrypted     = true
  kms_key_id            = aws_kms_key.rds.arn

  db_name  = "chartnav"
  username = "chartnav_app"
  password = random_password.db.result
  port     = 5432

  multi_az               = var.db_multi_az
  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  parameter_group_name   = aws_db_parameter_group.this.name
  publicly_accessible    = false

  backup_retention_period   = var.db_backup_retention_days
  backup_window             = "07:00-08:00"
  maintenance_window        = "sun:08:30-sun:09:30"
  copy_tags_to_snapshot     = true
  deletion_protection       = var.db_deletion_protection
  skip_final_snapshot       = false
  final_snapshot_identifier = "${local.name}-pg-final"

  # Point-in-time recovery is provided by automated backups (>0 retention).
  performance_insights_enabled    = true
  performance_insights_kms_key_id = aws_kms_key.rds.arn
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
  auto_minor_version_upgrade      = true

  tags = { Name = "${local.name}-pg" }
}
