#!/bin/bash
# =============================================================================
# Deploy Shichida Backend to EC2
# =============================================================================
# Prerequisites:
#   1. An EC2 instance running (Ubuntu 22.04 recommended)
#   2. SSH access to the instance
#   3. Security group allows inbound on ports 22 (SSH) and 8000 (or 80/443)
#
# Usage:
#   chmod +x deploy.sh
#   ./deploy.sh <ec2-public-ip> <ssh-key-path>
#
# Example:
#   ./deploy.sh 13.234.56.78 ~/.ssh/shichida-key.pem
# =============================================================================

EC2_IP=$1
SSH_KEY=$2

if [ -z "$EC2_IP" ] || [ -z "$SSH_KEY" ]; then
    echo "Usage: ./deploy.sh <ec2-ip> <ssh-key-path>"
    exit 1
fi

EC2_USER="ubuntu"
APP_DIR="/home/ubuntu/shichida_backend"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Deploying Shichida Backend to $EC2_IP"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Step 1: Install dependencies on EC2 (first time only)
echo ""
echo "[1/4] Setting up EC2 instance..."
ssh -i "$SSH_KEY" "$EC2_USER@$EC2_IP" << 'SETUP'
sudo apt-get update -qq
sudo apt-get install -y -qq python3-pip python3-venv nginx
if [ ! -d ~/shichida_backend/venv ]; then
    mkdir -p ~/shichida_backend
    python3 -m venv ~/shichida_backend/venv
fi
SETUP

# Step 2: Upload code
echo ""
echo "[2/4] Uploading code..."
rsync -avz --exclude='venv' --exclude='__pycache__' --exclude='db.sqlite3' \
    --exclude='.env' --exclude='*.pyc' --exclude='.git' \
    -e "ssh -i $SSH_KEY" \
    ./ "$EC2_USER@$EC2_IP:$APP_DIR/"

# Step 3: Upload .env.production
echo ""
echo "[3/4] Uploading production config..."
scp -i "$SSH_KEY" .env.production "$EC2_USER@$EC2_IP:$APP_DIR/.env"

# Step 4: Install deps, migrate, restart
echo ""
echo "[4/4] Installing dependencies and restarting..."
ssh -i "$SSH_KEY" "$EC2_USER@$EC2_IP" << DEPLOY
cd $APP_DIR
source venv/bin/activate
pip install -r requirements.txt -q
python manage.py migrate --noinput
python manage.py collectstatic --noinput

# Create systemd service
sudo tee /etc/systemd/system/shichida.service > /dev/null << 'SERVICE'
[Unit]
Description=Shichida Backend
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/shichida_backend
EnvironmentFile=/home/ubuntu/shichida_backend/.env
ExecStart=/home/ubuntu/shichida_backend/venv/bin/gunicorn schindia_backend.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 120
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
SERVICE

sudo systemctl daemon-reload
sudo systemctl enable shichida
sudo systemctl restart shichida

echo ""
echo "✅ Deployment complete! Server running on port 8000"
DEPLOY

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ Deployed successfully!"
echo "  API: http://$EC2_IP:8000/api/"
echo "  Admin: http://$EC2_IP:8000/admin/"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
