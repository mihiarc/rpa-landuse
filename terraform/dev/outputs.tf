# Output values for SSH key generation

# File Locations
output "private_key_file" {
  description = "Path to the private key file"
  value       = local_file.private_key.filename
}

output "key_pair_name" {
  description = "Name of the SSH key pair"
  value       = var.key_pair_name
}

# Sensitive Outputs (will be masked in terraform output)
output "private_key_pem" {
  description = "Private key in PEM format"
  value       = tls_private_key.ssh_key.private_key_pem
  sensitive   = true
}

output "public_key_openssh" {
  description = "Public key in OpenSSH format"
  value       = tls_private_key.ssh_key.public_key_openssh
  sensitive   = true
}
