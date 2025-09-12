# Generate SSH key pair locally (for AWS upload)
resource "tls_private_key" "ssh_key" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

# Create the SSH key pair in AWS
resource "aws_key_pair" "app_key" {
  key_name   = var.key_pair_name
  public_key = tls_private_key.ssh_key.public_key_openssh

  tags = {
    Name        = var.key_pair_name
    Environment = var.environment
    Project     = var.project_name
  }
}

# Store ONLY the private key in .ssh directory
resource "local_file" "private_key" {
  content         = tls_private_key.ssh_key.private_key_pem
  filename        = "${path.module}/.ssh/${var.key_pair_name}.pem"
  file_permission = "0400"
}

# Create the .ssh directory if it doesn't exist
resource "local_file" "ssh_directory" {
  content  = ""
  filename = "${path.module}/.ssh/.gitkeep"
}

# Create security group
resource "aws_security_group" "rpa_landuse_sg" {
  name        = "rpa-landuse-sg"
  description = "Security group for RPA Land Use Analytics application"
  vpc_id      = var.vpc_id

  # SSH access - restricted to specific IP
  ingress {
    description = "SSH access"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["65.190.52.97/32"]
  }

  # HTTP access - all IPs
  ingress {
    description = "HTTP access"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # HTTPS access - all IPs
  ingress {
    description = "HTTPS access"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # All outbound traffic
  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "rpa-landuse-sg"
    Environment = var.environment
    Project     = var.project_name
  }
}

# IAM role for EC2 instance to access Bedrock
resource "aws_iam_role" "ec2_bedrock_role" {
  name = "rpa-landuse-ec2-bedrock-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "rpa-landuse-ec2-bedrock-role"
    Environment = var.environment
    Project     = var.project_name
  }
}

# IAM policy for Bedrock Nova Lite access
resource "aws_iam_policy" "bedrock_nova_policy" {
  name        = "rpa-landuse-bedrock-nova-policy"
  description = "Policy for accessing AWS Bedrock Nova Lite model"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = "arn:aws:bedrock:${var.aws_region}::foundation-model/amazon.nova-lite-v1:0"
      }
    ]
  })

  tags = {
    Name        = "rpa-landuse-bedrock-nova-policy"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Attach policy to role
resource "aws_iam_role_policy_attachment" "bedrock_policy_attachment" {
  role       = aws_iam_role.ec2_bedrock_role.name
  policy_arn = aws_iam_policy.bedrock_nova_policy.arn
}

# Instance profile for EC2
resource "aws_iam_instance_profile" "ec2_profile" {
  name = "rpa-landuse-ec2-profile"
  role = aws_iam_role.ec2_bedrock_role.name

  tags = {
    Name        = "rpa-landuse-ec2-profile"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Get the latest Amazon Linux 2 AMI
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# Create EC2 instance
resource "aws_instance" "rpa_app_server" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = var.instance_type
  key_name               = aws_key_pair.app_key.key_name
  vpc_security_group_ids = [aws_security_group.rpa_landuse_sg.id]
  subnet_id              = var.subnet_id
  iam_instance_profile   = aws_iam_instance_profile.ec2_profile.name

  root_block_device {
    volume_type           = var.volume_type
    volume_size           = var.volume_size
    encrypted             = true
    delete_on_termination = true
  }

  tags = {
    Name        = var.instance_name
    Environment = var.environment
    Project     = var.project_name
  }
}
