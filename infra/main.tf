# ResultCloud on AWS: EC2 + RDS + S3 + IAM + CloudWatch
# terraform init && terraform apply   |   terraform destroy when done

terraform {
  required_providers {
    aws    = { source = "hashicorp/aws", version = "~> 6.0" }
    random = { source = "hashicorp/random", version = "~> 3.6" }
  }
}

provider "aws" {
  region = var.region
  default_tags { tags = { Project = "ResultCloud" } }
}

data "aws_vpc" "default" { default = true }

data "aws_ssm_parameter" "al2023" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}

resource "random_id" "suffix" { byte_length = 4 }

resource "random_password" "secret_key" {
  length  = 48
  special = false
}

# ---------------------------------------------------------------- S3
resource "aws_s3_bucket" "marksheets" {
  bucket        = "resultcloud-marksheets-${random_id.suffix.hex}"
  force_destroy = true # lets terraform destroy remove it with the PDFs inside
}

resource "aws_s3_bucket_public_access_block" "marksheets" {
  bucket                  = aws_s3_bucket.marksheets.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "marksheets" {
  bucket = aws_s3_bucket.marksheets.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}

# ---------------------------------------------------------------- IAM
resource "aws_iam_role" "ec2" {
  name = "ResultCloud-EC2-Role"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = "sts:AssumeRole", Principal = { Service = "ec2.amazonaws.com" } }]
  })
}

# least privilege: only put/get PDFs under marksheets/ in this one bucket
resource "aws_iam_role_policy" "s3_marksheets" {
  name = "ResultCloudS3Marksheets"
  role = aws_iam_role.ec2.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["s3:PutObject", "s3:GetObject"]
      Resource = "${aws_s3_bucket.marksheets.arn}/marksheets/*"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "cloudwatch_agent" {
  role       = aws_iam_role.ec2.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
}

resource "aws_iam_instance_profile" "ec2" {
  name = "ResultCloud-EC2-Profile"
  role = aws_iam_role.ec2.name
}

# ---------------------------------------------------------------- security groups
resource "aws_security_group" "web" {
  name   = "resultcloud-web-sg"
  vpc_id = data.aws_vpc.default.id

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  dynamic "ingress" {
    for_each = var.ssh_cidr == "" ? [] : [var.ssh_cidr]
    content {
      description = "SSH from my IP"
      from_port   = 22
      to_port     = 22
      protocol    = "tcp"
      cidr_blocks = [ingress.value]
    }
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "db" {
  name   = "resultcloud-db-sg"
  vpc_id = data.aws_vpc.default.id

  ingress {
    description     = "MySQL from the web server only"
    from_port       = 3306
    to_port         = 3306
    protocol        = "tcp"
    security_groups = [aws_security_group.web.id]
  }
}

# ---------------------------------------------------------------- RDS
resource "aws_db_instance" "mysql" {
  identifier             = "resultcloud-db"
  engine                 = "mysql"
  engine_version         = "8.0"
  instance_class         = var.db_instance_class
  allocated_storage      = 20
  storage_type           = "gp2" # free tier storage type
  db_name                = "resultcloud"
  username               = "admin"
  password               = var.db_password
  publicly_accessible    = false
  vpc_security_group_ids = [aws_security_group.db.id]
  storage_encrypted      = true
  skip_final_snapshot    = true
}

# ---------------------------------------------------------------- EC2
resource "aws_instance" "web" {
  ami                    = data.aws_ssm_parameter.al2023.value
  instance_type          = var.instance_type
  key_name               = var.key_name
  iam_instance_profile   = aws_iam_instance_profile.ec2.name
  vpc_security_group_ids = [aws_security_group.web.id]

  metadata_options { http_tokens = "required" } # IMDSv2 only

  root_block_device {
    volume_size = 20
    encrypted   = true
  }

  # first boot: clone the repo, write .env, run deploy/setup_ec2.sh
  user_data = templatefile("${path.module}/user_data.sh", {
    repo_url       = var.repo_url
    db_host        = aws_db_instance.mysql.address
    db_password    = var.db_password
    bucket         = aws_s3_bucket.marksheets.bucket
    region         = var.region
    secret_key     = random_password.secret_key.result
    admin_password = var.admin_password
  })

  tags = { Name = "resultcloud-web" }
}

# ---------------------------------------------------------------- CloudWatch
resource "aws_cloudwatch_log_group" "logs" {
  for_each          = toset(["resultcloud-app", "resultcloud-nginx-access", "resultcloud-nginx-error"])
  name              = each.key
  retention_in_days = 14
}

resource "aws_cloudwatch_metric_alarm" "cpu_high" {
  alarm_name          = "resultcloud-cpu-high"
  namespace           = "AWS/EC2"
  metric_name         = "CPUUtilization"
  dimensions          = { InstanceId = aws_instance.web.id }
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 1
  threshold           = 70
  comparison_operator = "GreaterThanThreshold"
}

resource "aws_cloudwatch_metric_alarm" "status_check" {
  alarm_name          = "resultcloud-status-check-failed"
  namespace           = "AWS/EC2"
  metric_name         = "StatusCheckFailed"
  dimensions          = { InstanceId = aws_instance.web.id }
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 2
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
}

resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "ResultCloud"
  dashboard_body = jsonencode({
    widgets = [
      { type = "metric", x = 0, y = 0, width = 12, height = 6, properties = {
        title = "EC2 CPU %", region = var.region, stat = "Average", period = 300
      metrics = [["AWS/EC2", "CPUUtilization", "InstanceId", aws_instance.web.id]] } },
      { type = "metric", x = 12, y = 0, width = 12, height = 6, properties = {
        title = "Memory used %", region = var.region, stat = "Average", period = 300
      metrics = [["ResultCloud", "mem_used_percent", "InstanceId", aws_instance.web.id]] } },
      { type = "log", x = 0, y = 6, width = 24, height = 6, properties = {
        title = "App errors", region = var.region
      query = "SOURCE 'resultcloud-app' | fields @timestamp, @message | filter @message like /ERROR|WARNING/ | sort @timestamp desc | limit 50" } },
    ]
  })
}
