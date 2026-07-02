#!/usr/bin/env bash
# .aws/setup.sh — ONE-TIME AWS infrastructure setup for Shichida Backend
#
# This creates:
#   - Secrets Manager entries (Django secret key, CORS, allowed hosts)
#   - CloudFormation stack (DynamoDB + ECS Fargate + ALB + EFS + ECR)
#   - GitHub OIDC trust + deploy role
#
# Usage:
#   AWS_PROFILE=shichida-admin AWS_REGION=ap-south-1 ./.aws/setup.sh
#
# Prerequisites:
#   - AWS CLI v2 configured with admin credentials
#   - A VPC with at least 2 public subnets

set -euo pipefail

REGION=${AWS_REGION:-ap-south-1}
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
GITHUB_ORG=${GITHUB_ORG:-omtechologiesai}
GITHUB_REPO=${GITHUB_REPO:-Shichida}

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Shichida Backend — AWS Setup"
echo "  Account : $ACCOUNT_ID"
echo "  Region  : $REGION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── 1. Create Secrets ──────────────────────────────────────────────────
echo ""
echo "[1/4] Creating Secrets Manager entries..."

# Generate a random Django secret key
DJANGO_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))" 2>/dev/null || openssl rand -base64 50)

create_secret() {
  local name=$1 value=$2
  if aws secretsmanager describe-secret --secret-id "$name" --region "$REGION" &>/dev/null; then
    echo "      $name — exists, updating..."
    aws secretsmanager put-secret-value --secret-id "$name" --secret-string "$value" --region "$REGION" > /dev/null
  else
    echo "      $name — creating..."
    aws secretsmanager create-secret --name "$name" --secret-string "$value" --region "$REGION" > /dev/null
  fi
}

create_secret "shichida/django-secret-key" "$DJANGO_KEY"
create_secret "shichida/allowed-hosts" "api.shichida.in,localhost"
create_secret "shichida/cors-origins" "https://admin.shichida.in,http://localhost:5173,http://localhost:3000"

# ── 2. Get VPC and Subnet info ────────────────────────────────────────
echo ""
echo "[2/4] Detecting VPC configuration..."

# Use default VPC
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" \
  --query "Vpcs[0].VpcId" --output text --region "$REGION")

if [ "$VPC_ID" = "None" ] || [ -z "$VPC_ID" ]; then
  echo "  ERROR: No default VPC found. Please specify VPC_ID manually."
  exit 1
fi

SUBNET_IDS=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" \
  --query "Subnets[?MapPublicIpOnLaunch==\`true\`].SubnetId" --output text --region "$REGION" | tr '\t' ',')

echo "      VPC: $VPC_ID"
echo "      Subnets: $SUBNET_IDS"

# ── 3. Deploy CloudFormation ──────────────────────────────────────────
echo ""
echo "[3/4] Deploying CloudFormation stack (this takes 5-10 minutes)..."
echo "      Stack: shichida-backend-infra"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

aws cloudformation deploy \
  --template-file "$SCRIPT_DIR/infrastructure.yaml" \
  --stack-name shichida-backend-infra \
  --parameter-overrides \
    "VpcId=$VPC_ID" \
    "SubnetIds=$SUBNET_IDS" \
  --capabilities CAPABILITY_NAMED_IAM \
  --region "$REGION" \
  --no-fail-on-empty-changeset

# Get outputs
ALB_URL=$(aws cloudformation describe-stacks --stack-name shichida-backend-infra \
  --query "Stacks[0].Outputs[?OutputKey=='ALBUrl'].OutputValue" --output text --region "$REGION")
ECR_URI=$(aws cloudformation describe-stacks --stack-name shichida-backend-infra \
  --query "Stacks[0].Outputs[?OutputKey=='ECRRepositoryUri'].OutputValue" --output text --region "$REGION")
EFS_ID=$(aws cloudformation describe-stacks --stack-name shichida-backend-infra \
  --query "Stacks[0].Outputs[?OutputKey=='EFSFileSystemId'].OutputValue" --output text --region "$REGION")

echo "      ALB URL : $ALB_URL"
echo "      ECR URI : $ECR_URI"
echo "      EFS ID  : $EFS_ID"

# ── 4. GitHub OIDC + Deploy Role ──────────────────────────────────────
echo ""
echo "[4/4] Setting up GitHub Actions OIDC..."

PROVIDER_ARN="arn:aws:iam::${ACCOUNT_ID}:oidc-provider/token.actions.githubusercontent.com"
if ! aws iam get-open-id-connect-provider --open-id-connect-provider-arn "$PROVIDER_ARN" &>/dev/null; then
  aws iam create-open-id-connect-provider \
    --url "https://token.actions.githubusercontent.com" \
    --client-id-list "sts.amazonaws.com" \
    --thumbprint-list "6938fd4d98bab03faadb97b34396831e3780aea1" > /dev/null
  echo "      OIDC provider created"
else
  echo "      OIDC provider exists"
fi

DEPLOY_ROLE=shichida-deploy-role
TRUST_POLICY=$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Federated": "$PROVIDER_ARN"},
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {"token.actions.githubusercontent.com:aud": "sts.amazonaws.com"},
      "StringLike": {"token.actions.githubusercontent.com:sub": "repo:${GITHUB_ORG}/${GITHUB_REPO}:*"}
    }
  }]
}
EOF
)

DEPLOY_ROLE_ARN=$(aws iam get-role --role-name "$DEPLOY_ROLE" --query Role.Arn --output text 2>/dev/null || true)
if [ -z "$DEPLOY_ROLE_ARN" ]; then
  DEPLOY_ROLE_ARN=$(aws iam create-role --role-name "$DEPLOY_ROLE" \
    --assume-role-policy-document "$TRUST_POLICY" --query Role.Arn --output text)
  echo "      Deploy role created: $DEPLOY_ROLE_ARN"
else
  aws iam update-assume-role-policy --role-name "$DEPLOY_ROLE" --policy-document "$TRUST_POLICY"
  echo "      Deploy role updated: $DEPLOY_ROLE_ARN"
fi

aws iam put-role-policy --role-name "$DEPLOY_ROLE" --policy-name deploy-permissions \
  --policy-document "{
    \"Version\": \"2012-10-17\",
    \"Statement\": [
      {
        \"Effect\": \"Allow\",
        \"Action\": [
          \"ecr:GetAuthorizationToken\",
          \"ecr:BatchCheckLayerAvailability\",
          \"ecr:GetDownloadUrlForLayer\",
          \"ecr:BatchGetImage\",
          \"ecr:InitiateLayerUpload\",
          \"ecr:UploadLayerPart\",
          \"ecr:CompleteLayerUpload\",
          \"ecr:PutImage\"
        ],
        \"Resource\": \"*\"
      },
      {
        \"Effect\": \"Allow\",
        \"Action\": [
          \"ecs:UpdateService\",
          \"ecs:DescribeServices\",
          \"ecs:DescribeTaskDefinition\",
          \"ecs:RegisterTaskDefinition\",
          \"ecs:RunTask\",
          \"ecs:DescribeTasks\"
        ],
        \"Resource\": \"*\"
      },
      {
        \"Effect\": \"Allow\",
        \"Action\": \"iam:PassRole\",
        \"Resource\": [
          \"arn:aws:iam::${ACCOUNT_ID}:role/shichida-ecs-execution-role\",
          \"arn:aws:iam::${ACCOUNT_ID}:role/shichida-ecs-task-role\"
        ]
      }
    ]
  }"

# ── Summary ───────────────────────────────────────────────────────────
cat <<SUMMARY

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✅  AWS Infrastructure Ready!

  API URL (ALB)        : $ALB_URL
  Container Registry   : $ECR_URI
  EFS (SQLite store)   : $EFS_ID
  Deploy Role          : $DEPLOY_ROLE_ARN

  DynamoDB tables provisioned by CloudFormation:
    - ShichidaInvoices
    - ShichidaCenters
    - ShichidaChildren
    - ShichidaUsers
    - ShichidaCentresTable
    - ShichidaRoles

  ─── Add these GitHub Secrets ──────────────────────────────

  AWS_DEPLOY_ROLE_ARN  = $DEPLOY_ROLE_ARN
  SUBNET_IDS           = $SUBNET_IDS
  SECURITY_GROUP_ID    = (from ECS security group in console)

  ─── First Deploy Steps ────────────────────────────────────

  1. Push Docker image:
     aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR_URI
     docker build -t $ECR_URI:latest .
     docker push $ECR_URI:latest

  2. Migrations run automatically in the container on startup
     (SQLite file lives at /data/db.sqlite3 on EFS)

  3. Create root admin (one-time):
     aws ecs run-task --cluster shichida-cluster \\
       --task-definition shichida-backend \\
       --launch-type FARGATE \\
       --network-configuration "..." \\
       --overrides '{"containerOverrides":[{"name":"shichida-backend","command":["python","manage.py","create_root","--name","Root Admin","--email","admin@shichida.in","--password","YOUR_PASSWORD"]}]}'

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SUMMARY
