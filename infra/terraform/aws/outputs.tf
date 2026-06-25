output "app_url" {
  description = "Public frontend URL."
  value       = "https://${var.app_hostname}"
}

output "api_url" {
  description = "Public API URL."
  value       = "https://${var.api_hostname}"
}

output "ecr_repository_url" {
  value = aws_ecr_repository.api.repository_url
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.this.name
}

output "ecs_service_name" {
  value = aws_ecs_service.api.name
}

output "api_task_definition_family" {
  value = aws_ecs_task_definition.api.family
}

output "frontend_bucket" {
  value = aws_s3_bucket.frontend.bucket
}

output "cloudfront_distribution_id" {
  value = aws_cloudfront_distribution.frontend.id
}

output "objects_bucket" {
  value = aws_s3_bucket.objects.bucket
}

output "rds_endpoint" {
  value     = aws_db_instance.this.address
  sensitive = true
}

output "database_url_secret_arn" {
  value = aws_secretsmanager_secret.database_url.arn
}

output "app_secret_arn" {
  value = aws_secretsmanager_secret.app.arn
}

output "private_subnet_ids" {
  value = aws_subnet.private[*].id
}

output "api_security_group_id" {
  value = aws_security_group.api.id
}

output "github_deploy_role_arn" {
  value       = var.github_repo == "" ? "" : aws_iam_role.github_deploy[0].arn
  description = "Role ARN GitHub Actions assumes via OIDC (empty if github_repo unset)."
}
