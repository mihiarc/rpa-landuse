# Variables for RPA Land Use Analytics Infrastructure

# Environment Configuration
variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Project name for resource naming and tagging"
  type        = string
  default     = "rpa-landuse"
}

# AWS Configuration
variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

# Existing Infrastructure (Data Sources)
variable "vpc_id" {
  description = "ID of existing VPC (leave empty to lookup by name)"
  type        = string
  default     = "vpc-607faf05"
}

variable "subnet_id" {
  description = "ID of existing subnet for EC2 instance (leave empty to use first public subnet)"
  type        = string
  default     = "subnet-dc0f1c9a"
}

# EC2 Configuration
variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3a.medium"
}

variable "instance_name" {
  description = "Name for the EC2 instance"
  type        = string
  default     = "rpa-app-server"
}

variable "key_pair_name" {
  description = "Name for the SSH key pair"
  type        = string
  default     = "rpa-landuse-key"
}

# Security Configuration
variable "allowed_ssh_cidr" {
  description = "CIDR block allowed for SSH access (0.0.0.0/0 for anywhere)"
  type        = string
  default     = "0.0.0.0/0"
}

variable "allowed_http_cidr" {
  description = "CIDR block allowed for HTTP access"
  type        = string
  default     = "0.0.0.0/0"
}

variable "allowed_https_cidr" {
  description = "CIDR block allowed for HTTPS access"
  type        = string
  default     = "0.0.0.0/0"
}

variable "volume_size" {
  description = "Size of the root EBS volume in GB"
  type        = number
  default     = 8
}

variable "volume_type" {
  description = "Type of EBS volume"
  type        = string
  default     = "gp3"
}
