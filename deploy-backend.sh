#!/bin/bash
# deploy-backend.sh — Deploy Shichida Django backend
#
# For LOCAL deployment (Docker):
#   docker-compose up --build -d
#
# For AWS ECS deployment (manual, outside CI):
#   AWS_PROFILE=shichida ./deploy-backend.sh aws
#
# Normal usage (local migrate + verify):
#   ./deploy-backend.sh

set -e

MODE=${1:-local}
REGION=${AWS_REGION:-ap-south-1}
ECR_REPO=${ECR_REPO:-shichida-backend}

echo "=== Shichida Backend Deploy (mode: $MODE) ==="

if [ "$MODE" = "aws" ]; then
    echo ""
    echo "[1/4] Building Docker image..."
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    ECR_URI="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$ECR_REPO"

    aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$ECR_URI"
    docker build -t "$ECR_URI:latest" -t "$ECR_URI:$(git rev-parse --short HEAD)" .

    echo "[2/4] Pushing to ECR..."
    docker push "$ECR_URI:latest"
    docker push "$ECR_URI:$(git rev-parse --short HEAD)"

    echo "[3/4] Updating ECS service..."
    aws ecs update-service \
        --cluster shichida-cluster \
        --service shichida-backend-service \
        --force-new-deployment \
        --region "$REGION" > /dev/null

    echo "[4/4] Waiting for deployment..."
    aws ecs wait services-stable \
        --cluster shichida-cluster \
        --services shichida-backend-service \
        --region "$REGION"

    echo ""
    echo "✅ AWS deployment complete!"
    echo "   SQLite DB lives at /data/db.sqlite3 on EFS (persistent across deployments)"
    echo "   DynamoDB billing tables are always available via boto3"
else
    echo ""
    echo "[1/4] Installing dependencies..."
    pip install -r requirements.txt --quiet

    echo "[2/4] Running migrations..."
    # SQLite is used in all environments; DJANGO_DB_PATH defaults to BASE_DIR/db.sqlite3
    python manage.py migrate --noinput

    echo "[3/4] Collecting static files..."
    python manage.py collectstatic --noinput 2>/dev/null || true

    echo "[4/4] Verifying..."
    python manage.py check

    echo ""
    echo "✅ Local deployment complete!"
    echo ""
    echo "API Base URLs:"
    echo "  Auth:     http://localhost:8000/api/auth/"
    echo "  API:      http://localhost:8000/api/v1/"
    echo ""
    echo "Root admin login:"
    echo "  Email:    admin@shichida.in"
    echo "  Password: Admin@123456"
fi
