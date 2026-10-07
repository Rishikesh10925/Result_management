output "app_url" {
  value = "http://${aws_instance.web.public_ip}/"
}

output "s3_bucket" {
  value = aws_s3_bucket.marksheets.bucket
}

output "rds_endpoint" {
  value = aws_db_instance.mysql.address
}

output "cloudwatch_dashboard" {
  value = "https://${var.region}.console.aws.amazon.com/cloudwatch/home?region=${var.region}#dashboards/dashboard/ResultCloud"
}
