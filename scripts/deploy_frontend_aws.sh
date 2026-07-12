#!/usr/bin/env bash
# CollabForge AI — frontend deployment: private S3 + CloudFront (OAC)
# Usage: BACKEND_URL=https://xxxx.awsapprunner.com ./scripts/deploy_frontend_aws.sh
set -euo pipefail
# Git Bash on Windows: stop MSYS mangling /paths in AWS CLI args
export MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL="*"

BUCKET_PREFIX="${BUCKET_PREFIX:-collabforge-frontend}"
[ -n "${BACKEND_URL:-}" ] || { echo "Set BACKEND_URL to the deployed App Runner URL"; exit 1; }

echo "==> Validating AWS identity"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="${AWS_REGION:-$(aws configure get region)}"
BUCKET="$BUCKET_PREFIX-$ACCOUNT_ID"

echo "==> 1/7 Ensuring private S3 bucket $BUCKET"
if ! aws s3api head-bucket --bucket "$BUCKET" 2>/dev/null; then
  if [ "$REGION" = "us-east-1" ]; then
    aws s3api create-bucket --bucket "$BUCKET" --region "$REGION" >/dev/null
  else
    aws s3api create-bucket --bucket "$BUCKET" --region "$REGION" \
      --create-bucket-configuration LocationConstraint="$REGION" >/dev/null
  fi
fi
aws s3api put-public-access-block --bucket "$BUCKET" \
  --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

echo "==> 2/7 Injecting backend URL into config"
# If BACKEND_URL is plain-HTTP (an ALB), CloudFront proxies /api/* + /health +
# /docs to it and the frontend calls same-origin, so we inject "" (same-origin).
PROXY_API=""
INJECT_URL="$BACKEND_URL"
case "$BACKEND_URL" in
  http://*) PROXY_API="yes"; INJECT_URL="" ;;
esac
# Use a relative repo-local build dir (Windows Python can't read MSYS /tmp
# or /e/... absolute paths; relative paths resolve fine)
BUILD_DIR=".frontend_build"
rm -rf "$BUILD_DIR"; mkdir -p "$BUILD_DIR"
cp -r frontend/. "$BUILD_DIR/"
python - "$BUILD_DIR/config.js" "$INJECT_URL" <<'PY'
import sys
p, url = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else "").rstrip("/")
s = open(p, encoding="utf-8").read().replace("__BACKEND_URL__", url)
open(p, "w", encoding="utf-8").write(s)
PY

echo "==> 3/7 Ensuring CloudFront distribution + OAC"
OAC_ID=$(aws cloudfront list-origin-access-controls \
  --query "OriginAccessControlList.Items[?Name=='collabforge-oac'].Id" --output text 2>/dev/null || true)
if [ -z "$OAC_ID" ] || [ "$OAC_ID" = "None" ]; then
  OAC_ID=$(aws cloudfront create-origin-access-control --origin-access-control-config \
    '{"Name":"collabforge-oac","OriginAccessControlOriginType":"s3","SigningBehavior":"always","SigningProtocol":"sigv4"}' \
    --query "OriginAccessControl.Id" --output text)
fi

DIST_ID=$(aws cloudfront list-distributions \
  --query "DistributionList.Items[?Comment=='collabforge-frontend'].Id | [0]" --output text 2>/dev/null || true)
if [ -z "$DIST_ID" ] || [ "$DIST_ID" = "None" ]; then
  BACKEND_HOST=$(echo "$BACKEND_URL" | sed -E 's#^https?://##; s#/.*$##')
  DIST_CFG=$(python - "$BUCKET" "$REGION" "$OAC_ID" "$PROXY_API" "$BACKEND_HOST" <<'PY'
import json, sys, time
bucket, region, oac, proxy, backend_host = sys.argv[1:6]
origins = [{
    "Id": "s3origin",
    "DomainName": f"{bucket}.s3.{region}.amazonaws.com",
    "OriginAccessControlId": oac,
    "S3OriginConfig": {"OriginAccessIdentity": ""},
}]
behaviors = []
if proxy:
    origins.append({
        "Id": "apiorigin",
        "DomainName": backend_host,
        "CustomOriginConfig": {
            "HTTPPort": 80, "HTTPSPort": 443,
            "OriginProtocolPolicy": "http-only",
            "OriginReadTimeout": 60, "OriginKeepaliveTimeout": 5,
        },
    })
    # CachingDisabled + AllViewerExceptHostHeader managed policies
    api_behavior = {
        "TargetOriginId": "apiorigin",
        "ViewerProtocolPolicy": "redirect-to-https",
        "CachePolicyId": "4135ea2d-6df8-44a3-9df3-4b5a84be39ad",
        "OriginRequestPolicyId": "b689b0a8-53d0-40ab-baf2-68738e2966ac",
        "AllowedMethods": {"Quantity": 7, "Items": ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"],
                            "CachedMethods": {"Quantity": 2, "Items": ["GET", "HEAD"]}},
        "Compress": False,
    }
    for pattern in ("/api/*", "/health", "/docs*", "/openapi.json"):
        behaviors.append({"PathPattern": pattern, **api_behavior})
cfg = {
  "CallerReference": str(time.time()),
  "Comment": "collabforge-frontend",
  "Enabled": True,
  "DefaultRootObject": "index.html",
  "Origins": {"Quantity": len(origins), "Items": origins},
  "DefaultCacheBehavior": {
    "TargetOriginId": "s3origin",
    "ViewerProtocolPolicy": "redirect-to-https",
    "CachePolicyId": "658327ea-f89d-4fab-a63d-7e88639e58f6",
    "Compress": True,
  },
  "CustomErrorResponses": {"Quantity": 1, "Items": [
    {"ErrorCode": 403, "ResponsePagePath": "/index.html", "ResponseCode": "200", "ErrorCachingMinTTL": 30},
  ]},
}
if behaviors:
    cfg["CacheBehaviors"] = {"Quantity": len(behaviors), "Items": behaviors}
print(json.dumps(cfg))
PY
)
  DIST_JSON=$(aws cloudfront create-distribution --distribution-config "$DIST_CFG")
  DIST_ID=$(echo "$DIST_JSON" | python -c "import json,sys;print(json.load(sys.stdin)['Distribution']['Id'])")
fi
DIST_DOMAIN=$(aws cloudfront get-distribution --id "$DIST_ID" --query "Distribution.DomainName" --output text)
DIST_ARN=$(aws cloudfront get-distribution --id "$DIST_ID" --query "Distribution.ARN" --output text)

echo "==> 4/7 Granting CloudFront read access to the bucket"
aws s3api put-bucket-policy --bucket "$BUCKET" --policy "{
  \"Version\":\"2012-10-17\",\"Statement\":[{
    \"Sid\":\"AllowCloudFront\",\"Effect\":\"Allow\",
    \"Principal\":{\"Service\":\"cloudfront.amazonaws.com\"},
    \"Action\":\"s3:GetObject\",\"Resource\":\"arn:aws:s3:::$BUCKET/*\",
    \"Condition\":{\"StringEquals\":{\"AWS:SourceArn\":\"$DIST_ARN\"}}}]}"

echo "==> 5/7 Uploading assets (correct MIME types + cache headers)"
# HTML + config: short cache so releases propagate
aws s3 cp "$BUILD_DIR" "s3://$BUCKET/" --recursive \
  --exclude "*" --include "*.html" --content-type "text/html; charset=utf-8" \
  --cache-control "public, max-age=60, must-revalidate" >/dev/null
aws s3 cp "$BUILD_DIR/config.js" "s3://$BUCKET/config.js" \
  --content-type "application/javascript; charset=utf-8" \
  --cache-control "public, max-age=60, must-revalidate" >/dev/null
# Static JS/CSS: long cache
aws s3 cp "$BUILD_DIR" "s3://$BUCKET/" --recursive \
  --exclude "*" --include "*.js" --exclude "config.js" \
  --content-type "application/javascript; charset=utf-8" \
  --cache-control "public, max-age=86400" >/dev/null
aws s3 cp "$BUILD_DIR" "s3://$BUCKET/" --recursive \
  --exclude "*" --include "*.css" --content-type "text/css; charset=utf-8" \
  --cache-control "public, max-age=86400" >/dev/null
rm -rf "$BUILD_DIR"

echo "==> 6/7 Invalidating CloudFront"
aws cloudfront create-invalidation --distribution-id "$DIST_ID" --paths "/*" >/dev/null

echo "==> 7/7 Testing"
echo "    waiting for distribution to deploy (this can take a few minutes)…"
for i in $(seq 1 40); do
  STATUS=$(aws cloudfront get-distribution --id "$DIST_ID" --query "Distribution.Status" --output text)
  [ "$STATUS" = "Deployed" ] && break
  sleep 15
done
curl -fsS -o /dev/null -w "landing page: HTTP %{http_code}\n" "https://$DIST_DOMAIN/" || true
curl -fsS "$BACKEND_URL/health" && echo " (backend health OK)"

echo "=================================================="
echo "Frontend deployed: https://$DIST_DOMAIN"
echo "Remember: update the backend FRONTEND_ORIGINS env to https://$DIST_DOMAIN"
echo "=================================================="
