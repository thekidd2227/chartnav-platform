# WAF with AWS managed rule sets + rate limiting. One ACL for the regional
# ALB, one (us-east-1) for the CloudFront distribution.

locals {
  managed_rule_groups = [
    "AWSManagedRulesCommonRuleSet",
    "AWSManagedRulesKnownBadInputsRuleSet",
    "AWSManagedRulesSQLiRuleSet",
    "AWSManagedRulesAmazonIpReputationList",
  ]
}

resource "aws_wafv2_web_acl" "alb" {
  name  = "${local.name}-alb"
  scope = "REGIONAL"
  default_action { allow {} }

  dynamic "rule" {
    for_each = local.managed_rule_groups
    content {
      name     = rule.value
      priority = rule.key + 1
      override_action { none {} }
      statement {
        managed_rule_group_statement {
          name        = rule.value
          vendor_name = "AWS"
        }
      }
      visibility_config {
        cloudwatch_metrics_enabled = true
        metric_name                = "${local.name}-${rule.value}"
        sampled_requests_enabled   = true
      }
    }
  }

  rule {
    name     = "rate-limit"
    priority = 100
    action { block {} }
    statement {
      rate_based_statement {
        limit              = 2000
        aggregate_key_type = "IP"
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${local.name}-rate-limit"
      sampled_requests_enabled   = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "${local.name}-alb"
    sampled_requests_enabled   = true
  }
}

resource "aws_wafv2_web_acl_association" "alb" {
  resource_arn = aws_lb.api.arn
  web_acl_arn  = aws_wafv2_web_acl.alb.arn
}

resource "aws_wafv2_web_acl" "cloudfront" {
  provider = aws.us_east_1
  name     = "${local.name}-cloudfront"
  scope    = "CLOUDFRONT"
  default_action { allow {} }

  dynamic "rule" {
    for_each = local.managed_rule_groups
    content {
      name     = rule.value
      priority = rule.key + 1
      override_action { none {} }
      statement {
        managed_rule_group_statement {
          name        = rule.value
          vendor_name = "AWS"
        }
      }
      visibility_config {
        cloudwatch_metrics_enabled = true
        metric_name                = "${local.name}-cf-${rule.value}"
        sampled_requests_enabled   = true
      }
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "${local.name}-cloudfront"
    sampled_requests_enabled   = true
  }
}
