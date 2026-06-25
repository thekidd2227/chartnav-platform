# Least-privilege security groups. ALB is the only public ingress; the API
# task only accepts traffic from the ALB; RDS only from the API task.

resource "aws_security_group" "alb" {
  name        = "${local.name}-alb"
  description = "Public ALB ingress (443)."
  vpc_id      = aws_vpc.this.id

  ingress {
    description = "HTTPS from the internet"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${local.name}-alb" }
}

resource "aws_security_group" "api" {
  name        = "${local.name}-api"
  description = "API task: ingress only from the ALB."
  vpc_id      = aws_vpc.this.id

  ingress {
    description     = "From ALB"
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${local.name}-api" }
}

resource "aws_security_group" "rds" {
  name        = "${local.name}-rds"
  description = "PostgreSQL: ingress only from the API task SG."
  vpc_id      = aws_vpc.this.id

  ingress {
    description     = "PostgreSQL from API"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.api.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${local.name}-rds" }
}
