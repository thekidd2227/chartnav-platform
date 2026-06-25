# Secrets Manager — application secrets + the assembled DATABASE_URL.
# Values are placeholders here; real values are set out-of-band (console/CLI)
# or rotated by the IdP/ops. Terraform never stores live secrets in state on
# purpose — see ignore_changes below.

resource "aws_secretsmanager_secret" "app" {
  name       = "${local.name}/app"
  kms_key_id = aws_kms_key.secrets.arn
  tags       = { Name = "${local.name}-app" }
}

resource "random_password" "secret_key" {
  length  = 48
  special = false
}

resource "random_password" "session_secret" {
  length  = 48
  special = false
}

resource "aws_secretsmanager_secret_version" "app" {
  secret_id = aws_secretsmanager_secret.app.id
  secret_string = jsonencode({
    secret_key     = random_password.secret_key.result
    session_secret = random_password.session_secret.result
    # IdP wiring is set by ops after the OIDC app is created.
    jwt_issuer   = "REPLACE_WITH_IDP_ISSUER"
    jwt_audience = "chartnav-api"
    jwt_jwks_url = "REPLACE_WITH_IDP_JWKS_URL"
  })

  lifecycle {
    ignore_changes = [secret_string] # ops/IdP own the live values after first apply
  }
}

# Assembled libpq URL with TLS required. Password from the RDS resource.
resource "aws_secretsmanager_secret" "database_url" {
  name       = "${local.name}/database-url"
  kms_key_id = aws_kms_key.secrets.arn
  tags       = { Name = "${local.name}-database-url" }
}

resource "aws_secretsmanager_secret_version" "database_url" {
  secret_id = aws_secretsmanager_secret.database_url.id
  secret_string = format(
    "postgresql+psycopg://%s:%s@%s:%s/%s?sslmode=require",
    aws_db_instance.this.username,
    random_password.db.result,
    aws_db_instance.this.address,
    aws_db_instance.this.port,
    aws_db_instance.this.db_name,
  )
}
