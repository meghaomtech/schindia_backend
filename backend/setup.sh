#!/usr/bin/env bash
# setup.sh — ONE-TIME infrastructure setup for Shichida Admin on AWS
#
# Run this once from your laptop with your own AWS credentials:
#   AWS_PROFILE=my-profile AWS_REGION=ap-south-1 ./setup.sh
#
# After this script runs you will never need personal credentials again.
# All future deployments happen through GitHub Actions assuming a role.

set -euo pipefail

REGION=${AWS_REGION:-ap-south-1}
GITHUB_ORG=omtechologiesai
GITHUB_REPO=Shichida

# Resource names (all derived from one prefix)
PREFIX=shichida
TABLE_NAME=ShichidaInvoices
LAMBDA_NAME=${PREFIX}-invoices
LAMBDA_ROLE=${PREFIX}-lambda-role
API_NAME=${PREFIX}-invoices-api
DEPLOY_ROLE=${PREFIX}-deploy-role
CF_STACK=${PREFIX}-frontend
BUCKET_NAME=${PREFIX}-frontend-$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "unknown")
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

AWS_CLI_OPTS=()
[ -n "${AWS_PROFILE:-}" ] && AWS_CLI_OPTS=(--profile "$AWS_PROFILE")
aws() { command aws "${AWS_CLI_OPTS[@]}" "$@"; }

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
BUCKET_NAME="${PREFIX}-frontend-${ACCOUNT_ID}"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Shichida Admin — AWS Infrastructure Setup"
echo "  Account : $ACCOUNT_ID"
echo "  Region  : $REGION"
echo "  Identity: $(aws sts get-caller-identity --query Arn --output text)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── 1. DynamoDB ───────────────────────────────────────────────────────
echo ""
echo "[1/7] DynamoDB table: $TABLE_NAME"
if aws dynamodb describe-table --table-name "$TABLE_NAME" --region "$REGION" &>/dev/null; then
  echo "      Already exists — skipping"
else
  aws dynamodb create-table \
    --table-name "$TABLE_NAME" \
    --attribute-definitions AttributeName=invoiceNumber,AttributeType=S \
    --key-schema AttributeName=invoiceNumber,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region "$REGION" > /dev/null
  aws dynamodb wait table-exists --table-name "$TABLE_NAME" --region "$REGION"
  echo "      Created ✓"
fi

# ── 2. Lambda execution role ──────────────────────────────────────────
echo ""
echo "[2/7] Lambda execution role: $LAMBDA_ROLE"
LAMBDA_ROLE_ARN=$(aws iam get-role --role-name "$LAMBDA_ROLE" \
  --query Role.Arn --output text 2>/dev/null || true)
if [ -z "$LAMBDA_ROLE_ARN" ]; then
  LAMBDA_ROLE_ARN=$(aws iam create-role \
    --role-name "$LAMBDA_ROLE" \
    --assume-role-policy-document '{
      "Version":"2012-10-17",
      "Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]
    }' --query Role.Arn --output text)
  aws iam attach-role-policy --role-name "$LAMBDA_ROLE" \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
  aws iam put-role-policy --role-name "$LAMBDA_ROLE" \
    --policy-name ddb-access \
    --policy-document "{
      \"Version\":\"2012-10-17\",
      \"Statement\":[{
        \"Effect\":\"Allow\",
        \"Action\":[\"dynamodb:PutItem\",\"dynamodb:GetItem\",\"dynamodb:Scan\",\"dynamodb:UpdateItem\",\"dynamodb:DeleteItem\"],
        \"Resource\":\"arn:aws:dynamodb:$REGION:$ACCOUNT_ID:table/$TABLE_NAME\"
      }]
    }"
  echo "      Created: $LAMBDA_ROLE_ARN — waiting 12s for IAM propagation..."
  sleep 12
else
  echo "      Exists: $LAMBDA_ROLE_ARN"
fi

# ── 3. Lambda function ─────────────────────────────────────────────────
echo ""
echo "[3/7] Lambda function: $LAMBDA_NAME"
LAMBDA_ARN=$(aws lambda get-function --function-name "$LAMBDA_NAME" --region "$REGION" \
  --query Configuration.FunctionArn --output text 2>/dev/null || true)

if [ -z "$LAMBDA_ARN" ]; then
  # Build a minimal bootstrap zip (real code deployed by deploy.sh / CI)
  BOOTSTRAP_ZIP="/tmp/shichida-bootstrap.zip"
  mkdir -p /tmp/shichida-bootstrap
  echo 'export const handler = async () => ({ statusCode: 200, body: "ok" });' \
    > /tmp/shichida-bootstrap/index.mjs
  (cd /tmp/shichida-bootstrap && zip -q "$BOOTSTRAP_ZIP" index.mjs)

  LAMBDA_ARN=$(aws lambda create-function \
    --function-name "$LAMBDA_NAME" \
    --runtime nodejs20.x \
    --role "$LAMBDA_ROLE_ARN" \
    --handler index.handler \
    --zip-file "fileb://$BOOTSTRAP_ZIP" \
    --environment "Variables={TABLE_NAME=$TABLE_NAME}" \
    --timeout 15 \
    --memory-size 256 \
    --region "$REGION" \
    --query FunctionArn --output text)
  aws lambda wait function-active --function-name "$LAMBDA_NAME" --region "$REGION"
  echo "      Created: $LAMBDA_ARN"
else
  echo "      Exists: $LAMBDA_ARN"
fi

# ── 4. API Gateway ────────────────────────────────────────────────────
echo ""
echo "[4/7] HTTP API Gateway: $API_NAME"
EXISTING_API=$(aws apigatewayv2 get-apis --region "$REGION" \
  --query "Items[?Name=='$API_NAME'].ApiId | [0]" --output text 2>/dev/null || true)

if [ -z "$EXISTING_API" ] || [ "$EXISTING_API" = "None" ]; then
  API_ID=$(aws apigatewayv2 create-api \
    --name "$API_NAME" \
    --protocol-type HTTP \
    --cors-configuration AllowOrigins='["*"]',AllowMethods='["GET","POST","OPTIONS"]',AllowHeaders='["Content-Type"]' \
    --region "$REGION" --query ApiId --output text)
  echo "      Created API: $API_ID"
else
  API_ID="$EXISTING_API"
  echo "      Exists: $API_ID"
fi

aws lambda add-permission \
  --function-name "$LAMBDA_NAME" \
  --statement-id "apigw-$(date +%s)" \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:$REGION:$ACCOUNT_ID:$API_ID/*/*" \
  --region "$REGION" > /dev/null 2>&1 || true

INTEGRATION_ID=$(aws apigatewayv2 get-integrations --api-id "$API_ID" --region "$REGION" \
  --query "Items[0].IntegrationId" --output text 2>/dev/null || true)
if [ -z "$INTEGRATION_ID" ] || [ "$INTEGRATION_ID" = "None" ]; then
  INTEGRATION_ID=$(aws apigatewayv2 create-integration \
    --api-id "$API_ID" \
    --integration-type AWS_PROXY \
    --integration-uri "$LAMBDA_ARN" \
    --payload-format-version "2.0" \
    --region "$REGION" --query IntegrationId --output text)
fi

TARGET="integrations/$INTEGRATION_ID"
for ROUTE in "POST /invoices" "GET /invoices" "GET /invoices/{invoiceNumber}"; do
  EXISTS=$(aws apigatewayv2 get-routes --api-id "$API_ID" --region "$REGION" \
    --query "Items[?RouteKey=='$ROUTE'].RouteId | [0]" --output text 2>/dev/null || true)
  [ -z "$EXISTS" ] || [ "$EXISTS" = "None" ] && \
    aws apigatewayv2 create-route --api-id "$API_ID" \
      --route-key "$ROUTE" --target "$TARGET" --region "$REGION" > /dev/null
done

STAGE_EXISTS=$(aws apigatewayv2 get-stages --api-id "$API_ID" --region "$REGION" \
  --query "Items[?StageName=='prod'].StageName | [0]" --output text 2>/dev/null || true)
[ -z "$STAGE_EXISTS" ] || [ "$STAGE_EXISTS" = "None" ] && \
  aws apigatewayv2 create-stage --api-id "$API_ID" \
    --stage-name prod --auto-deploy --region "$REGION" > /dev/null

API_URL="https://$API_ID.execute-api.$REGION.amazonaws.com/prod"
echo "      API URL: $API_URL"

# ── 5. S3 + CloudFront (via CloudFormation) ────────────────────────────
echo ""
echo "[5/7] Frontend hosting: S3 + CloudFront (stack: $CF_STACK)"
echo "      Note: CloudFront takes 5-10 minutes to provision..."
aws cloudformation deploy \
  --template-file "$SCRIPT_DIR/cloudfront.yaml" \
  --stack-name "$CF_STACK" \
  --parameter-overrides "BucketName=$BUCKET_NAME" \
  --capabilities CAPABILITY_IAM \
  --region us-east-1 \
  --no-fail-on-empty-changeset

# CloudFront stacks must be in us-east-1 for ACM certs, but the bucket
# is regional — here we just use the bucket in the same stack.
CLOUDFRONT_URL=$(aws cloudformation describe-stacks \
  --stack-name "$CF_STACK" --region us-east-1 \
  --query "Stacks[0].Outputs[?OutputKey=='CloudFrontUrl'].OutputValue" --output text)
DIST_ID=$(aws cloudformation describe-stacks \
  --stack-name "$CF_STACK" --region us-east-1 \
  --query "Stacks[0].Outputs[?OutputKey=='DistributionId'].OutputValue" --output text)

echo "      CloudFront URL : $CLOUDFRONT_URL"
echo "      Distribution ID: $DIST_ID"

# ── 6. GitHub OIDC provider ───────────────────────────────────────────
echo ""
echo "[6/7] GitHub OIDC trust"
PROVIDER_ARN="arn:aws:iam::${ACCOUNT_ID}:oidc-provider/token.actions.githubusercontent.com"
if aws iam get-open-id-connect-provider --open-id-connect-provider-arn "$PROVIDER_ARN" &>/dev/null; then
  echo "      Already exists"
else
  aws iam create-open-id-connect-provider \
    --url "https://token.actions.githubusercontent.com" \
    --client-id-list "sts.amazonaws.com" \
    --thumbprint-list "6938fd4d98bab03faadb97b34396831e3780aea1" > /dev/null
  echo "      Created"
fi

# ── 7. Deploy role (assumed by GitHub Actions) ────────────────────────
echo ""
echo "[7/7] Deploy role: $DEPLOY_ROLE"
DEPLOY_ROLE_ARN=$(aws iam get-role --role-name "$DEPLOY_ROLE" \
  --query Role.Arn --output text 2>/dev/null || true)

TRUST=$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Federated": "$PROVIDER_ARN"},
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
      },
      "StringLike": {
        "token.actions.githubusercontent.com:sub": "repo:${GITHUB_ORG}/${GITHUB_REPO}:*"
      }
    }
  }]
}
EOF
)

if [ -z "$DEPLOY_ROLE_ARN" ]; then
  DEPLOY_ROLE_ARN=$(aws iam create-role \
    --role-name "$DEPLOY_ROLE" \
    --assume-role-policy-document "$TRUST" \
    --query Role.Arn --output text)
  echo "      Created: $DEPLOY_ROLE_ARN"
else
  aws iam update-assume-role-policy --role-name "$DEPLOY_ROLE" \
    --policy-document "$TRUST"
  echo "      Updated trust: $DEPLOY_ROLE_ARN"
fi

aws iam put-role-policy --role-name "$DEPLOY_ROLE" \
  --policy-name deploy-permissions \
  --policy-document "{
    \"Version\": \"2012-10-17\",
    \"Statement\": [
      {
        \"Sid\": \"Lambda\",
        \"Effect\": \"Allow\",
        \"Action\": [\"lambda:UpdateFunctionCode\",\"lambda:GetFunction\",\"lambda:GetFunctionConfiguration\",\"lambda:UpdateFunctionConfiguration\"],
        \"Resource\": \"arn:aws:lambda:$REGION:$ACCOUNT_ID:function:$LAMBDA_NAME\"
      },
      {
        \"Sid\": \"S3\",
        \"Effect\": \"Allow\",
        \"Action\": [\"s3:PutObject\",\"s3:DeleteObject\",\"s3:GetObject\",\"s3:ListBucket\"],
        \"Resource\": [
          \"arn:aws:s3:::$BUCKET_NAME\",
          \"arn:aws:s3:::$BUCKET_NAME/*\"
        ]
      },
      {
        \"Sid\": \"CloudFront\",
        \"Effect\": \"Allow\",
        \"Action\": \"cloudfront:CreateInvalidation\",
        \"Resource\": \"arn:aws:cloudfront::$ACCOUNT_ID:distribution/$DIST_ID\"
      },
      {
        \"Sid\": \"STS\",
        \"Effect\": \"Allow\",
        \"Action\": \"sts:GetCallerIdentity\",
        \"Resource\": \"*\"
      }
    ]
  }"
echo "      Permissions attached"

# ── Summary ───────────────────────────────────────────────────────────
cat <<SUMMARY

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✅  Infrastructure ready!

  App URL (CloudFront) : $CLOUDFRONT_URL
  API URL (API Gateway): $API_URL

  ─── Add these to GitHub (Settings → Secrets & variables) ───

  SECRET  AWS_DEPLOY_ROLE_ARN = $DEPLOY_ROLE_ARN

  VARIABLE  AWS_REGION           = $REGION
  VARIABLE  AWS_S3_BUCKET        = $BUCKET_NAME
  VARIABLE  AWS_CF_DIST_ID       = $DIST_ID
  VARIABLE  VITE_INVOICES_API_URL = $API_URL

  ─── Push to main to trigger your first full deploy ──────────
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SUMMARY
