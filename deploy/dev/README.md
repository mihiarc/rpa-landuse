# RPA Land Use Analytics - Deployment Script

## Overview

Automated deployment script for deploying the RPA Land Use Analytics application to EC2 instances using Bash + Docker approach with comprehensive logging.

## Prerequisites

- **SSH Key**: Provide the `.pem` file for EC2 instance access
- **AWS CLI**: Configured with appropriate permissions for EC2 describe operations
- **Local Environment**: Bash shell with `rsync`, `zip`, and `ssh` utilities

## Deployment Process

### 1. Pre-Deployment Checks

```bash

aws ecr get-login-password --region us-east-1 --profile afrancis-cds | docker login --username AWS --password-stdin 810875545305.dkr.ecr.us-east-1.amazonaws.com

# EC2 instance status verification
aws ec2 describe-instances --instance-ids <instance-id> --query 'Reservations[0].Instances[0].State.Name'

# SSH connectivity test
ssh -i <key-file>.pem -o ConnectTimeout=10 ec2-user@<instance-ip> 'echo "SSH OK"'
ssh -i ~/.ssh/rpa-landuse-key.pem -o ConnectTimeout=10 ec2-user@34.207.249.14 'echo "SSH OK"'

# Docker installation check
ssh -i <key-file>.pem ec2-user@<instance-ip> 'docker --version || echo "Docker not installed"'
ssh -i ~/.ssh/rpa-landuse-key.pem ec2-user@34.207.249.14 'docker --version || echo "Docker not installed"'

# Docker installation (if needed)

# System update status
ssh -i <key-file>.pem ec2-user@<instance-ip> 'sudo yum check-update --security | wc -l'
```

### 2. Application File Preparation

**Files to Deploy** (based on docker-compose volumes):

```
landuse_app.py          # Main application
src/                    # Source code directory
views/                  # Application views
data/                   # Data files
config/                 # Configuration files
docker/                 # Docker configuration
.env.dev               # Environment variables
```

**Packaging:**

```bash
# Create deployment archive excluding unnecessary files
zip -r app-deployment.zip \
  ../../landuse_app.py ../../requirements.txt ../../src/ ../../views/ ../../data/ ../../docker/prod \
  --exclude="*.git*" "*.terraform*" "**/__pycache__*" "*.pyc"
```

### 3. File Transfer & Deployment

```bash
# Transfer application archive
rsync -avz -e "ssh -i <key-file>.pem" app-deployment.zip ec2-user@<instance-ip>:~/landuse-app/2025-12-09
rsync -avz -e "ssh -i ~/.ssh/rpa-landuse-key.pem" app-deployment.zip ec2-user@34.207.249.14:~/landuse-app/2025-12-09/

# Remote deployment execution
ssh -i <key-file>.pem ec2-user@<instance-ip> << 'EOF'
  # Extract application
  unzip -o ~/landuse-app/2025-12-09/app-deployment.zip -d ~/app/

  # Stop existing services
  cd ~/app && docker-compose down

  # Start new deployment
  docker-compose -f docker/dev/docker-compose.yml up -d --build
EOF
```

## Deployment Script Features

### Logging Strategy

- **Timestamp Logging**: All operations timestamped
- **Status Checks**: Pre/post deployment validation
- **Error Handling**: Detailed error messages with exit codes
- **Progress Indicators**: Step-by-step deployment progress
- **Rollback Capability**: Automatic rollback on critical failures

### Health Checks

```bash
# System health verification
- EC2 instance state (running/stopped)
- Docker daemon status
- Available disk space (>1GB recommended)
- Memory usage (<80% recommended)
- Network connectivity to Docker registry

# Application health verification
- Container startup status
- Port accessibility (8501)
- Application response test
- Log file creation
```

### Error Handling

- **SSH Connection**: Retry mechanism with exponential backoff
- **File Transfer**: Verification of transfer completion
- **Docker Operations**: Container health checks before proceeding
- **Service Validation**: Post-deployment connectivity tests

## Usage

### Basic Deployment

```bash
# Set deployment variables
export EC2_INSTANCE_ID="i-1234567890abcdef0"
export SSH_KEY_PATH="path/to/key.pem"
export EC2_HOST="ec2-user@<instance-ip>"

# Run deployment script
./deploy.sh
```

### Script Configuration

```bash
# deploy.sh configuration variables
LOG_LEVEL="INFO"                    # DEBUG, INFO, WARN, ERROR
DEPLOYMENT_TIMEOUT="300"            # Deployment timeout in seconds
HEALTH_CHECK_RETRIES="5"           # Number of health check attempts
BACKUP_BEFORE_DEPLOY="true"        # Create backup before deployment
ROLLBACK_ON_FAILURE="true"         # Auto rollback on deployment failure
```

## Deployment Logs

**Log Locations:**

- Local: `./deploy-$(date +%Y%m%d-%H%M%S).log`
- Remote: `~/app/deploy.log`

**Log Levels:**

- `INFO`: Standard deployment progress
- `WARN`: Non-critical issues (e.g., optional components)
- `ERROR`: Critical failures requiring attention
- `DEBUG`: Detailed operation traces

## Troubleshooting

### Common Issues

1. **SSH Connection Failed**: Verify security group allows SSH from your IP
2. **Docker Not Found**: Script will attempt installation if missing
3. **Insufficient Disk Space**: Cleanup old containers/images
4. **Port 8501 Unavailable**: Check for existing services on port

### Manual Verification

```bash
# Check application status
curl -f http://<instance-ip>:8501/health || echo "Application not responding"

# View container logs
ssh -i <key-file>.pem ec2-user@<instance-ip> 'docker-compose logs --tail=50'

# System resource check
ssh -i <key-file>.pem ec2-user@<instance-ip> 'df -h && free -h'
```
