# TerahBank — Root Terraform configuration
# AWS af-south-1 (Cape Town) — CEMAC data residency requirement
# Apply per environment: cd envs/staging && terraform apply

terraform {
  required_version = ">= 1.7.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Remote state — S3 backend (bucket provisioned manually before first apply)
  backend "s3" {
    bucket         = "terahbank-terraform-state"
    key            = "global/terraform.tfstate"
    region         = "af-south-1"
    encrypt        = true
    dynamodb_table = "terahbank-terraform-locks"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "TerahBank"
      ManagedBy   = "Terraform"
      Environment = var.environment
    }
  }
}
