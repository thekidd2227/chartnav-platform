# Private container registry + ECS Fargate API service. The migration command
# is a SEPARATE one-off task (run by the deploy pipeline), not the service.

resource "aws_ecr_repository" "api" {
  name                 = "${var.project}/api"
  image_tag_mutability = "IMMUTABLE"
  image_scanning_configuration { scan_on_push = true }
  encryption_configuration {
    encryption_type = "KMS"
    kms_key         = aws_kms_key.s3.arn
  }
  tags = { Name = "${local.name}-api" }
}

resource "aws_ecs_cluster" "this" {
  name = local.name
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
  tags = { Name = local.name }
}

resource "aws_ecs_cluster_capacity_providers" "this" {
  cluster_name       = aws_ecs_cluster.this.name
  capacity_providers = ["FARGATE"]
  default_capacity_provider_strategy {
    capacity_provider = "FARGATE"
    weight            = 1
  }
}

locals {
  api_base_env = merge({
    CHARTNAV_ENV         = "prod"
    CHARTNAV_AUTH_MODE   = "bearer"
    CHARTNAV_API_URL     = "https://${var.api_hostname}"
    CHARTNAV_APP_URL     = "https://${var.app_hostname}"
    CHARTNAV_CORS_ALLOW_ORIGINS = "https://${var.app_hostname}"
    CHARTNAV_STORAGE_BACKEND    = "s3"
    CHARTNAV_S3_BUCKET          = aws_s3_bucket.objects.bucket
    CHARTNAV_S3_KMS_KEY_ID      = aws_kms_key.s3.arn
    CHARTNAV_BACKUPS_CONFIGURED = "true"
    AWS_REGION                  = var.aws_region
  }, var.app_environment_extra)
}

# Steady-state API service container definition.
resource "aws_ecs_task_definition" "api" {
  family                   = "${local.name}-api"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.api_cpu
  memory                   = var.api_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.api_task.arn

  container_definitions = jsonencode([
    {
      name      = "api"
      image     = var.api_image
      essential = true
      command   = ["./entrypoint.sh", "serve"]
      portMappings = [{ containerPort = 8000, protocol = "tcp" }]
      environment = [for k, v in local.api_base_env : { name = k, value = tostring(v) }]
      secrets = [
        { name = "DATABASE_URL", valueFrom = aws_secretsmanager_secret.database_url.arn },
        { name = "CHARTNAV_SECRET_KEY", valueFrom = "${aws_secretsmanager_secret.app.arn}:secret_key::" },
        { name = "CHARTNAV_SESSION_SECRET", valueFrom = "${aws_secretsmanager_secret.app.arn}:session_secret::" },
        { name = "CHARTNAV_JWT_ISSUER", valueFrom = "${aws_secretsmanager_secret.app.arn}:jwt_issuer::" },
        { name = "CHARTNAV_JWT_AUDIENCE", valueFrom = "${aws_secretsmanager_secret.app.arn}:jwt_audience::" },
        { name = "CHARTNAV_JWT_JWKS_URL", valueFrom = "${aws_secretsmanager_secret.app.arn}:jwt_jwks_url::" },
      ]
      readonlyRootFilesystem = true
      stopTimeout            = 30
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.api.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "api"
        }
      }
      healthCheck = {
        command     = ["CMD-SHELL", "curl -fsS http://localhost:8000/readyz || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 30
      }
    }
  ])

  tags = { Name = "${local.name}-api" }
}

resource "aws_ecs_service" "api" {
  name            = "${local.name}-api"
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.api_desired_count
  launch_type     = "FARGATE"

  deployment_minimum_healthy_percent = 100
  deployment_maximum_percent         = 200
  health_check_grace_period_seconds  = 60

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.api.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = 8000
  }

  depends_on = [aws_lb_listener.https]
  tags       = { Name = "${local.name}-api" }

  lifecycle {
    ignore_changes = [task_definition] # pipeline updates the task def revision
  }
}
