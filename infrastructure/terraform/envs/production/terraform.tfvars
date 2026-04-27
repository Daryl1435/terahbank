# Production environment — fill in sensitive values via CI secrets, not here
environment       = "production"
aws_region        = "af-south-1"
db_instance_class = "db.t3.large"
redis_node_type   = "cache.t3.small"
api_cpu           = 512
api_memory        = 1024
api_desired_count = 2
