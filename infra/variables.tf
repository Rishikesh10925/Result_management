variable "region" {
  default = "ap-south-1" # Mumbai
}

variable "repo_url" {
  description = "Public GitHub URL of this repo; EC2 clones it on first boot"
}

variable "db_password" {
  description = "RDS master password (8+ chars, no / @ \" or spaces)"
  sensitive   = true
}

variable "admin_password" {
  description = "Password for the ResultCloud 'admin' login (8+ chars)"
  sensitive   = true
}

variable "ssh_cidr" {
  description = "Your IP for SSH, e.g. 49.36.10.20/32. Leave empty to keep SSH closed."
  default     = ""
}

variable "key_name" {
  description = "Existing EC2 key pair name for SSH (optional)"
  default     = null
}

variable "instance_type" {
  default = "t3.micro" # free tier
}

variable "db_instance_class" {
  default = "db.t4g.micro" # free tier
}
