#!/usr/bin/env bash
# deploy.sh — re-deploy Lambda code + React frontend
#
# Called by GitHub Actions after setup.sh has been run once.
# All resources already exist; this script only updates code.
#
# Required env vars (set as GitHub Actions variables):
#   AWS_REGION
#   AWS_S3_BUCKET
#   AWS_CF_DIST_ID
#   VITE_INVOICES_API_URL
#
# Run locally:
#   AWS_PROFILE=my-profile \
#   AWS_REGION=ap-south-1 \
#   AWS_S3_BUCKET=shichida-frontend-<accountid> \
#   AWS_CF_DIST_ID=EXXXXXXXXX \
#   VITE_INVOICES_API_URL=https://xxxx.execute-api.ap-south-1.amazonaws.com/prod \
#   ./backend/deploy.sh

set -euo pipefail

: "${AWS_REGION:?Set AWS_REGION}"
: "${AWS_S3_BUCKET:?Set AWS_S3_BUCKET}"
: "${AWS_CF_DIST_ID:?Set AWS_CF_DIST_ID}"
: "${VITE_INVOICES_API_URL:?Set VITE_INVOICES_API_URL}"

LAMBDA_NAME=shichida-invoices
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ZIP_PATH="/tmp/shichida-lambda.zip"

AWS_CLI_OPTS=()
[ -n "${AWS_PROFILE:-}" ] && AWS_CLI_OPTS=(--profile "$AWS_PROFILE")
aws() { command aws "${AWS_CLI_OPTS[@]}" "$@"; }

echo "==> Region: $AWS_REGION  Bucket: $AWS_S3_BUCKET  CF: $AWS_CF_DIST_ID"

# ── 1. Build and deploy Lambda ────────────────────────────────────────
echo ""
echo "[1/3] Lambda: building..."
cd "$SCRIPT_DIR/lambda"
npm install --silent --omit=dev
rm -f "$ZIP_PATH"
zip -r "$ZIP_PATH" . -x "*.zip" > /dev/null
echo "      Zip: $(du -sh "$ZIP_PATH" | cut -f1)"

echo "      Updating function code..."
aws lambda update-function-code \
  --function-name "$LAMBDA_NAME" \
  --zip-file "fileb://$ZIP_PATH" \
  --region "$AWS_REGION" > /dev/null
aws lambda wait function-updated \
  --function-name "$LAMBDA_NAME" \
  --region "$AWS_REGION"
echo "      Lambda deployed ✓"

# ── 2. Build React frontend ───────────────────────────────────────────
echo ""
echo "[2/3] Frontend: building..."
cd "$ROOT_DIR"
npm ci --silent
VITE_INVOICES_API_URL="$VITE_INVOICES_API_URL" npm run build
echo "      Build output: dist/"

# ── 3. Sync to S3 + invalidate CloudFront ────────────────────────────
echo ""
echo "[3/3] Uploading to S3..."
aws s3 sync dist/ "s3://$AWS_S3_BUCKET/" \
  --delete \
  --cache-control "public,max-age=31536000,immutable" \
  --exclude "index.html" \
  --region "$AWS_REGION"

# index.html must not be cached (always fetch latest)
aws s3 cp dist/index.html "s3://$AWS_S3_BUCKET/index.html" \
  --cache-control "no-cache,no-store,must-revalidate" \
  --region "$AWS_REGION"

echo "      Invalidating CloudFront cache..."
aws cloudfront create-invalidation \
  --distribution-id "$AWS_CF_DIST_ID" \
  --paths "/*" \
  --query Invalidation.Id --output text

echo ""
echo "✅ Deploy complete!"
