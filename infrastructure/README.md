# TerahBank Infrastructure

Terraform for AWS af-south-1 (Cape Town) — mandatory for CEMAC data residency.

## Structure

```
terraform/
├── main.tf          ← Provider, backend (S3 remote state)
├── variables.tf     ← All input variables with validation
├── outputs.tf       ← Key outputs (ECR URL, RDS endpoint, etc.)
├── ecr.tf           ← Container registry
├── s3.tf            ← KYC docs + audit log buckets (KMS encrypted)
├── envs/
│   ├── staging/terraform.tfvars
│   └── production/terraform.tfvars
```

## First-time setup

1. Manually create the S3 state bucket and DynamoDB lock table (done once):
```bash
aws s3 mb s3://terahbank-terraform-state --region af-south-1
aws dynamodb create-table \
  --table-name terahbank-terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region af-south-1
```

2. Apply staging:
```bash
cd terraform/envs/staging
terraform init -backend-config="key=staging/terraform.tfstate"
terraform plan -var="db_password=$DB_PASSWORD"
terraform apply -var="db_password=$DB_PASSWORD"
```

3. Apply production (requires production AWS credentials):
```bash
cd terraform/envs/production
terraform init -backend-config="key=production/terraform.tfstate"
terraform plan -var="db_password=$DB_PASSWORD"
terraform apply -var="db_password=$DB_PASSWORD"
```
