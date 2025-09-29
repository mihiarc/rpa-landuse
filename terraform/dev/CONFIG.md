# RPA Land Use Analytics - Infrastructure Overview

## Architecture

**Existing AWS Infrastructure (not managed by Terraform):**

- VPC: `vpc-607faf05`
- Subnet: `subnet-dc0f1c9a`
- Internet Gateway & Route Tables

**Terraform-Managed Resources:**

- **EC2 Instance**: `t3a.medium` with 8GB gp3 storage
- **Security Group**: SSH (65.190.52.97 only), HTTP/HTTPS (public)
- **SSH Key Pair**: 4096-bit RSA, stored in `.ssh/rpa-landuse-key.pem`
- **IAM Role**: EC2 instance profile with Bedrock Nova Lite model access only

## Quick Start

### 1. Deploy Infrastructure

```bash
cd docker/dev && docker-compose up -d terraform-dev
docker exec -it rpa-terraform-dev /bin/bash
cd /workspace && terraform init && terraform apply
```

### 2. Connect to Instance

```bash
# SSH access
ssh -i .ssh/rpa-landuse-key.pem ec2-user@<instance-ip>

# Get instance IP
terraform output
```

### 3. Run Application

```bash
cd ../../docker/dev
docker-compose up -d streamlit-app
# Access at http://localhost:8501
```

## Docker Services

- **terraform-dev**: Terraform + AWS CLI for infrastructure management
- **streamlit-app**: Application runtime environment

## Management

- **Infrastructure**: Managed via Terraform in Docker container
- **Application**: Deployed via Docker Compose
- **SSH Keys**: Auto-generated and stored in `.ssh/` directory
- **Security**: IP-restricted SSH, public HTTP/HTTPS access
- **IAM Access**: Instance profile enables credential-free Bedrock API calls
