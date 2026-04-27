# Staging environment — fill in sensitive values via CI secrets, not here
environment       = "staging"
aws_region        = "af-south-1"
db_instance_class = "db.t3.medium"
redis_node_type   = "cache.t3.micro"
api_cpu           = 256
api_memory        = 512
api_desired_count = 1
