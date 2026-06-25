# Private, encrypted, versioned object bucket for clinical artifacts.
# Public access fully blocked. Lifecycle transitions + (documented) Object Lock.

resource "aws_s3_bucket" "objects" {
  bucket = "${local.name}-objects"
  tags   = { Name = "${local.name}-objects" }
}

resource "aws_s3_bucket_public_access_block" "objects" {
  bucket                  = aws_s3_bucket.objects.id
  block_public_acls       = true
  block_public_policy      = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "objects" {
  bucket = aws_s3_bucket.objects.id
  rule { object_ownership = "BucketOwnerEnforced" }
}

resource "aws_s3_bucket_versioning" "objects" {
  bucket = aws_s3_bucket.objects.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "objects" {
  bucket = aws_s3_bucket.objects.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.s3.arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "objects" {
  bucket = aws_s3_bucket.objects.id

  rule {
    id     = "transition-and-expire-noncurrent"
    status = "Enabled"

    transition {
      days          = 90
      storage_class = "STANDARD_IA"
    }
    noncurrent_version_transition {
      noncurrent_days = 30
      storage_class   = "STANDARD_IA"
    }
    noncurrent_version_expiration {
      noncurrent_days = 365
    }
    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# Enforce TLS-only access to the bucket.
data "aws_iam_policy_document" "objects_tls_only" {
  statement {
    sid       = "DenyInsecureTransport"
    effect    = "Deny"
    actions   = ["s3:*"]
    resources = [aws_s3_bucket.objects.arn, "${aws_s3_bucket.objects.arn}/*"]
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

resource "aws_s3_bucket_policy" "objects" {
  bucket = aws_s3_bucket.objects.id
  policy = data.aws_iam_policy_document.objects_tls_only.json
}

# ── Optional: immutable audit-export bucket with Object Lock ────────────
# Object Lock (WORM) for immutable audit exports must be enabled AT BUCKET
# CREATION. Design documented in docs/security/audit-logging.md. Provided here
# but governance-gated; enable per compliance review.
#
# resource "aws_s3_bucket" "audit_exports" {
#   bucket              = "${local.name}-audit-exports"
#   object_lock_enabled = true
# }
# resource "aws_s3_bucket_object_lock_configuration" "audit_exports" {
#   bucket = aws_s3_bucket.audit_exports.id
#   rule { default_retention { mode = "COMPLIANCE" years = 7 } }
# }
