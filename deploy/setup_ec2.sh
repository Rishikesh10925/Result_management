#!/bin/bash
# One-time setup on an Amazon Linux 2023 EC2 instance.
# Run from the cloned repo:  bash deploy/setup_ec2.sh
set -e
APP=/home/ec2-user/ResultCloud
cd "$APP"

echo "== packages"
sudo dnf install -y python3.11 python3.11-pip nginx git amazon-cloudwatch-agent

echo "== node (only needed to build the React app)"
if ! command -v node >/dev/null; then
  curl -fsSL https://nodejs.org/dist/v22.20.0/node-v22.20.0-linux-x64.tar.xz | sudo tar -xJ -C /usr/local --strip-components=1
fi

echo "== backend"
python3.11 -m venv backend/venv
backend/venv/bin/pip install -q -r backend/requirements.txt

echo "== frontend"
(cd frontend && npm ci && npm run build)

echo "== logs"
sudo mkdir -p /var/log/resultcloud
sudo chown ec2-user /var/log/resultcloud

if [ ! -f .env ]; then
  echo "!! Create $APP/.env first (see .env.example), then run this again."
  exit 1
fi

echo "== database tables + admin"
(cd backend && venv/bin/flask --app app init-db)

echo "== gunicorn service"
sudo cp deploy/resultcloud.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now resultcloud

echo "== nginx"
sudo cp deploy/nginx.conf /etc/nginx/conf.d/resultcloud.conf
sudo systemctl enable --now nginx
sudo systemctl reload nginx

echo "== cloudwatch agent"
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a fetch-config -m ec2 -s -c file:"$APP/deploy/cloudwatch-agent.json"

echo "== done: open http://$(curl -s http://checkip.amazonaws.com)/"
