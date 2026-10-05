#!/bin/bash
# Pull the latest code and restart. Run on EC2:  bash deploy/update.sh
set -e
cd /home/ec2-user/ResultCloud
git pull
backend/venv/bin/pip install -q -r backend/requirements.txt
(cd frontend && npm ci && npm run build)
sudo systemctl restart resultcloud
echo "updated"
