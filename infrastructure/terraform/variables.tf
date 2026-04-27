variable "aws_region" {
  description = "AWS region — must be af-south-1 for CEMAC data residency"
  type        = string
  default     = "af-south-1"

  validation {
    condition     = var.aws_region == "af-south-1"
    error_message = "CEMAC compliance requires af-south-1 (Cape Town). No other region permitted."
  }
}

variable "environment" {
  description = "Deployment environment"
  type        = string

  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "Must be 'staging' or 'production'."
  }
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.medium"
}

variable "db_allocated_storage_gb" {
  description = "RDS allocated storage in GB"
  type        = number
  default     = 20
}

variable "db_password" {
  description = "PostgreSQL master password (store in GitHub Secrets / AWS Secrets Manager)"
  type        = string
  sensitive   = true
}

variable "redis_node_type" {
  description = "ElastiCache Redis node type"
  type        = string
  default     = "cache.t3.micro"
}

variable "api_cpu" {
  description = "ECS task CPU units for API"
  type        = number
  default     = 512
}

variable "api_memory" {
  description = "ECS task memory (MB) for API"
  type        = number
  default     = 1024
}

variable "api_desired_count" {
  description = "Desired number of ECS API tasks"
  type        = number
  default     = 2
}

variable "ecr_image_tag" {
  description = "Docker image tag to deploy"
  type        = string
  default     = "latest"
}
