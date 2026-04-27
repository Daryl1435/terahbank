# S3 — KYC document storage + audit log archive
# All buckets: server-side encryption, versioning, no public access

resource "aws_s3_bucket" "kyc_documents" {
  bucket = "terahbank-kyc-documents-${var.environment}"
}

resource "aws_s3_bucket_versioning" "kyc_documents" {
  bucket = aws_s3_bucket.kyc_documents.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "kyc_documents" {
  bucket = aws_s3_bucket.kyc_documents.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.terahbank.arn
    }
  }
}

resource "aws_s3_bucket_public_access_block" "kyc_documents" {
  bucket                  = aws_s3_bucket.kyc_documents.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Audit log archive — Object Lock (Compliance mode, 7-year retention)
# COBAC compliance requirement
resource "aws_s3_bucket" "audit_logs" {
  bucket              = "terahbank-audit-logs-${var.environment}"
  object_lock_enabled = true
}

resource "aws_s3_bucket_object_lock_configuration" "audit_logs" {
  bucket = aws_s3_bucket.audit_logs.id
  rule {
    default_retention {
      mode  = "COMPLIANCE"
      years = 7
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "audit_logs" {
  bucket = aws_s3_bucket.audit_logs.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.terahbank.arn
    }
  }
}

resource "aws_s3_bucket_public_access_block" "audit_logs" {
  bucket                  = aws_s3_bucket.audit_logs.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# KMS key for all S3 encryption + RDS encryption
resource "aws_kms_key" "terahbank" {
  description             = "TerahBank master encryption key — ${var.environment}"
  deletion_window_in_days = 30
  enable_key_rotation     = true
}

resource "aws_kms_alias" "terahbank" {
  name          = "alias/terahbank-${var.environment}"
  target_key_id = aws_kms_key.terahbank.key_id
}
