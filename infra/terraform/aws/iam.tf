# Least-privilege roles: ECS execution (pull image, read secrets for injection),
# API task (scoped S3 + KMS + Secrets), and a GitHub-OIDC deploy role (no
# long-lived keys).

# ── ECS execution role (used by the agent to start the task) ───────────
resource "aws_iam_role" "ecs_execution" {
  name               = "${local.name}-ecs-execution"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

data "aws_iam_policy_document" "ecs_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role_policy_attachment" "ecs_execution_managed" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "ecs_execution_secrets" {
  name = "secrets-read"
  role = aws_iam_role.ecs_execution.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = [aws_secretsmanager_secret.app.arn, aws_secretsmanager_secret.database_url.arn]
      },
      {
        Effect   = "Allow"
        Action   = ["kms:Decrypt"]
        Resource = [aws_kms_key.secrets.arn]
      }
    ]
  })
}

# ── API task role (the application's own permissions) ──────────────────
resource "aws_iam_role" "api_task" {
  name               = "${local.name}-api-task"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

resource "aws_iam_role_policy" "api_task" {
  name = "app-permissions"
  role = aws_iam_role.api_task.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ObjectsRW"
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
        Resource = ["${aws_s3_bucket.objects.arn}/*"]
      },
      {
        Sid      = "ObjectsList"
        Effect   = "Allow"
        Action   = ["s3:ListBucket"]
        Resource = [aws_s3_bucket.objects.arn]
      },
      {
        Sid      = "ObjectKms"
        Effect   = "Allow"
        Action   = ["kms:GenerateDataKey", "kms:Decrypt"]
        Resource = [aws_kms_key.s3.arn]
      }
    ]
  })
}

# ── GitHub Actions OIDC deploy role (no long-lived AWS keys) ───────────
variable "github_repo" {
  description = "owner/repo allowed to assume the deploy role via OIDC."
  type        = string
  default     = ""
}

data "aws_iam_openid_connect_provider" "github" {
  count = var.github_repo == "" ? 0 : 1
  url   = "https://token.actions.githubusercontent.com"
}

data "aws_iam_policy_document" "github_assume" {
  count = var.github_repo == "" ? 0 : 1
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [data.aws_iam_openid_connect_provider.github[0].arn]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }
    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${var.github_repo}:*"]
    }
  }
}

resource "aws_iam_role" "github_deploy" {
  count              = var.github_repo == "" ? 0 : 1
  name               = "${local.name}-github-deploy"
  assume_role_policy = data.aws_iam_policy_document.github_assume[0].json
}

resource "aws_iam_role_policy" "github_deploy" {
  count = var.github_repo == "" ? 0 : 1
  name  = "deploy"
  role  = aws_iam_role.github_deploy[0].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = ["ecr:GetAuthorizationToken"], Resource = "*" },
      {
        Effect   = "Allow"
        Action   = ["ecr:BatchCheckLayerAvailability", "ecr:CompleteLayerUpload", "ecr:InitiateLayerUpload", "ecr:PutImage", "ecr:UploadLayerPart", "ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"]
        Resource = [aws_ecr_repository.api.arn]
      },
      {
        Effect   = "Allow"
        Action   = ["ecs:RegisterTaskDefinition", "ecs:DescribeServices", "ecs:UpdateService", "ecs:DescribeTaskDefinition", "ecs:RunTask", "ecs:DescribeTasks", "ecs:ListTasks"]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["s3:PutObject", "s3:DeleteObject", "s3:ListBucket"]
        Resource = [aws_s3_bucket.frontend.arn, "${aws_s3_bucket.frontend.arn}/*"]
      },
      {
        Effect   = "Allow"
        Action   = ["cloudfront:CreateInvalidation"]
        Resource = [aws_cloudfront_distribution.frontend.arn]
      },
      {
        Effect   = "Allow"
        Action   = ["iam:PassRole"]
        Resource = [aws_iam_role.ecs_execution.arn, aws_iam_role.api_task.arn]
      }
    ]
  })
}
