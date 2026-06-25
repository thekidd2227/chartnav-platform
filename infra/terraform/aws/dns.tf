# ACM certificates (DNS-validated) + Route 53 records for the app + API.
# The API cert is regional (for the ALB); the frontend cert is us-east-1
# (required by CloudFront).

# ── API certificate (regional) ────────────────────────────────────────
resource "aws_acm_certificate" "api" {
  domain_name       = var.api_hostname
  validation_method = "DNS"
  lifecycle { create_before_destroy = true }
  tags = { Name = "${local.name}-api" }
}

resource "aws_route53_record" "api_cert_validation" {
  for_each = {
    for o in aws_acm_certificate.api.domain_validation_options : o.domain_name => {
      name = o.resource_record_name, type = o.resource_record_type, record = o.resource_record_value
    }
  }
  zone_id = var.route53_zone_id
  name    = each.value.name
  type    = each.value.type
  records = [each.value.record]
  ttl     = 60
}

resource "aws_acm_certificate_validation" "api" {
  certificate_arn         = aws_acm_certificate.api.arn
  validation_record_fqdns = [for r in aws_route53_record.api_cert_validation : r.fqdn]
}

# ── Frontend certificate (us-east-1 for CloudFront) ────────────────────
resource "aws_acm_certificate" "frontend" {
  provider          = aws.us_east_1
  domain_name       = var.app_hostname
  validation_method = "DNS"
  lifecycle { create_before_destroy = true }
  tags = { Name = "${local.name}-frontend" }
}

resource "aws_route53_record" "frontend_cert_validation" {
  for_each = {
    for o in aws_acm_certificate.frontend.domain_validation_options : o.domain_name => {
      name = o.resource_record_name, type = o.resource_record_type, record = o.resource_record_value
    }
  }
  zone_id = var.route53_zone_id
  name    = each.value.name
  type    = each.value.type
  records = [each.value.record]
  ttl     = 60
}

resource "aws_acm_certificate_validation" "frontend" {
  provider                = aws.us_east_1
  certificate_arn         = aws_acm_certificate.frontend.arn
  validation_record_fqdns = [for r in aws_route53_record.frontend_cert_validation : r.fqdn]
}

# ── Alias records ──────────────────────────────────────────────────────
resource "aws_route53_record" "api" {
  zone_id = var.route53_zone_id
  name    = var.api_hostname
  type    = "A"
  alias {
    name                   = aws_lb.api.dns_name
    zone_id                = aws_lb.api.zone_id
    evaluate_target_health = true
  }
}

resource "aws_route53_record" "app" {
  zone_id = var.route53_zone_id
  name    = var.app_hostname
  type    = "A"
  alias {
    name                   = aws_cloudfront_distribution.frontend.domain_name
    zone_id                = aws_cloudfront_distribution.frontend.hosted_zone_id
    evaluate_target_health = false
  }
}
