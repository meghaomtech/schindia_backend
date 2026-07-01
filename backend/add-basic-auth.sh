#!/usr/bin/env bash
# add-basic-auth.sh — adds password protection to the CloudFront distribution
#
# Usage:
#   AWS_PROFILE=shichida-setup AWS_REGION=ap-south-1 \
#   USERNAME=admin PASSWORD=yourpassword ./add-basic-auth.sh
#
# To change the password later, just re-run this script with the new values.

set -euo pipefail

: "${USERNAME:?Set USERNAME=yourname}"
: "${PASSWORD:?Set PASSWORD=yourpassword}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CF_STACK=shichida-frontend
BUCKET_NAME="shichida-frontend-$(aws sts get-caller-identity --query Account --output text)"

AWS_CLI_OPTS=()
[ -n "${AWS_PROFILE:-}" ] && AWS_CLI_OPTS=(--profile "$AWS_PROFILE")
aws() { command aws "${AWS_CLI_OPTS[@]}" "$@"; }

AUTH_BASE64=$(echo -n "${USERNAME}:${PASSWORD}" | base64)
echo "==> Protecting CloudFront with Basic Auth"
echo "    Username : $USERNAME"
echo "    Password : $PASSWORD"
echo "    Encoded  : $AUTH_BASE64"
echo ""
echo "    Updating CloudFormation stack (this re-deploys CloudFront — takes ~3 min)..."

aws cloudformation deploy \
  --template-file "$SCRIPT_DIR/cloudfront.yaml" \
  --stack-name "$CF_STACK" \
  --parameter-overrides \
    "BucketName=$BUCKET_NAME" \
    "AuthBase64=$AUTH_BASE64" \
  --capabilities CAPABILITY_IAM \
  --region us-east-1 \
  --no-fail-on-empty-changeset

CF_URL=$(aws cloudformation describe-stacks \
  --stack-name "$CF_STACK" --region us-east-1 \
  --query "Stacks[0].Outputs[?OutputKey=='CloudFrontUrl'].OutputValue" --output text)

echo ""
echo "✅ Done! Your app is now password protected."
echo ""
echo "   URL      : $CF_URL"
echo "   Username : $USERNAME"
echo "   Password : $PASSWORD"
echo ""
echo "Share only this URL with your team — not the password in plaintext."
