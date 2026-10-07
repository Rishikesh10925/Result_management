#!/bin/bash
# Runs once as root on the EC2 instance's first boot (output: /var/log/cloud-init-output.log)
set -e
dnf install -y git
cd /home/ec2-user
sudo -u ec2-user git clone ${repo_url} ResultCloud

cat > ResultCloud/.env <<'EOF'
DB_HOST=${db_host}
DB_PORT=3306
DB_NAME=resultcloud
DB_USER=admin
DB_PASSWORD=${db_password}
S3_BUCKET=${bucket}
AWS_REGION=${region}
SECRET_KEY=${secret_key}
ADMIN_PASSWORD=${admin_password}
LOG_FILE=/var/log/resultcloud/app.log
HTTPS=0
EOF
chown ec2-user:ec2-user ResultCloud/.env
chmod 600 ResultCloud/.env

sudo -u ec2-user -H bash -c 'cd /home/ec2-user/ResultCloud && bash deploy/setup_ec2.sh'
