# Terraform Development Environment

A containerized Terraform development environment with all necessary tools pre-installed.

## Features

- **Terraform** (v1.6.6) - Infrastructure as Code
- **Terragrunt** (v0.54.8) - Terraform wrapper for DRY configurations
- **AWS CLI v2** - AWS command line interface
- **tfenv** - Terraform version management
- **tflint** - Terraform linting
- **checkov** - Security and compliance scanning
- **pre-commit** - Git hooks for code quality

## Quick Start

### 1. Build and Run the Container

```bash
# Navigate to the docker/dev directory
cd docker/dev

# Build and start the container
docker-compose up -d terraform-dev

# Connect to the container
docker-compose exec terraform-dev bash
```

### 2. Alternative: Run with Docker directly

```bash
# Build the image
docker build -t rpa-terraform-dev .

# Run the container
docker run -it \
  -v $(pwd)/../../:/workspace \
  -v ~/.aws:/home/terraform/.aws:ro \
  --name terraform-dev \
  rpa-terraform-dev
```

## Usage

### Inside the Container

```bash
# Initialize Terraform
terraform init

# Plan infrastructure changes
terraform plan

# Apply changes
terraform apply

# Use aliases
tf plan    # Short for terraform plan
tg plan    # Terragrunt plan

# Lint your Terraform code
tflint

# Security scanning
checkov -d .

# AWS CLI
aws sts get-caller-identity
```

### AWS Credentials

**Option 1: Mount AWS credentials directory**

```bash
# Ensure your ~/.aws directory has credentials and config
docker run -v ~/.aws:/home/terraform/.aws:ro ...
```

**Option 2: Use environment variables**

```bash
docker run \
  -e AWS_ACCESS_KEY_ID=your_access_key \
  -e AWS_SECRET_ACCESS_KEY=your_secret_key \
  -e AWS_REGION=us-east-1 \
  ...
```

**Option 3: Configure inside container**

```bash
# Inside the container
aws configure
```

## Directory Structure

```
/workspace          # Your project root (mounted)
/home/terraform     # User home directory
  ├── .aws/         # AWS credentials
  ├── .ssh/         # SSH keys
  ├── .terraform.d/ # Terraform plugins cache
  └── infrastructure/ # Terraform configurations
```

## Terraform Configuration Examples

### Basic AWS Provider

```hcl
# providers.tf
terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}
```

### Variables

```hcl
# variables.tf
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}
```

## Management Commands

```bash
# Start the container
docker-compose up -d terraform-dev

# Connect to running container
docker-compose exec terraform-dev bash

# Stop the container
docker-compose stop terraform-dev

# Remove container and volumes
docker-compose down -v

# View logs
docker-compose logs terraform-dev

# Rebuild container
docker-compose build terraform-dev
```

## Troubleshooting

### Permission Issues

```bash
# Fix AWS credentials permissions
chmod 600 ~/.aws/credentials
chmod 644 ~/.aws/config

# Fix SSH key permissions
chmod 600 ~/.ssh/id_rsa
chmod 644 ~/.ssh/id_rsa.pub
```

### AWS Authentication

```bash
# Test AWS credentials
aws sts get-caller-identity

# Configure new profile
aws configure --profile myprofile
```

### Container Issues

```bash
# Check container status
docker-compose ps

# Access container with root privileges
docker-compose exec --user root terraform-dev bash

# Check container logs
docker-compose logs terraform-dev
```
