#!/usr/bin/env bash
# CollabForge AI — backend deployment: Docker → ECR → AWS App Runner
# Secrets are read from backend/.env and passed as runtime env vars;
# they are never printed or baked into the image.
set -euo pipefail
# Git Bash on Windows: stop MSYS mangling /paths in AWS CLI args
export MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL="*"

APP_NAME="${APP_NAME:-collabforge-backend}"
ECR_REPO="${ECR_REPO:-collabforge-backend}"
DDB_TABLE="${DDB_TABLE:-collabforge-campaigns}"
MEDIA_BUCKET_PREFIX="${MEDIA_BUCKET_PREFIX:-collabforge-media}"

echo "==> 1/11 Validating AWS identity"
aws sts get-caller-identity --query Arn --output text
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="${AWS_REGION:-$(aws configure get region)}"
[ -n "$REGION" ] || { echo "No AWS region configured"; exit 1; }
echo "    account=$ACCOUNT_ID region=$REGION"

echo "==> 2/11 Ensuring ECR repository"
aws ecr describe-repositories --repository-names "$ECR_REPO" --region "$REGION" >/dev/null 2>&1 \
  || aws ecr create-repository --repository-name "$ECR_REPO" --region "$REGION" >/dev/null
ECR_URI="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$ECR_REPO"

echo "==> 3/11 Ensuring DynamoDB table $DDB_TABLE"
if ! aws dynamodb describe-table --table-name "$DDB_TABLE" --region "$REGION" >/dev/null 2>&1; then
  aws dynamodb create-table --table-name "$DDB_TABLE" \
    --attribute-definitions AttributeName=pk,AttributeType=S AttributeName=sk,AttributeType=S \
    --key-schema AttributeName=pk,KeyType=HASH AttributeName=sk,KeyType=RANGE \
    --billing-mode PAY_PER_REQUEST --region "$REGION" >/dev/null
  aws dynamodb wait table-exists --table-name "$DDB_TABLE" --region "$REGION"
fi

echo "==> 4/11 Ensuring media S3 bucket"
MEDIA_BUCKET="$MEDIA_BUCKET_PREFIX-$ACCOUNT_ID"
if ! aws s3api head-bucket --bucket "$MEDIA_BUCKET" 2>/dev/null; then
  if [ "$REGION" = "us-east-1" ]; then
    aws s3api create-bucket --bucket "$MEDIA_BUCKET" --region "$REGION" >/dev/null
  else
    aws s3api create-bucket --bucket "$MEDIA_BUCKET" --region "$REGION" \
      --create-bucket-configuration LocationConstraint="$REGION" >/dev/null
  fi
  aws s3api put-public-access-block --bucket "$MEDIA_BUCKET" \
    --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
fi

echo "==> 5/11 Ensuring IAM roles"
# ECR access role (for App Runner to pull the image)
ACCESS_ROLE="collabforge-apprunner-access"
if ! aws iam get-role --role-name "$ACCESS_ROLE" >/dev/null 2>&1; then
  aws iam create-role --role-name "$ACCESS_ROLE" --assume-role-policy-document '{
    "Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"build.apprunner.amazonaws.com"},"Action":"sts:AssumeRole"}]}' >/dev/null
  aws iam attach-role-policy --role-name "$ACCESS_ROLE" \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess
  sleep 10
fi
# Instance role (S3 + DynamoDB, least privilege)
INSTANCE_ROLE="collabforge-apprunner-instance"
if ! aws iam get-role --role-name "$INSTANCE_ROLE" >/dev/null 2>&1; then
  aws iam create-role --role-name "$INSTANCE_ROLE" --assume-role-policy-document '{
    "Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"tasks.apprunner.amazonaws.com"},"Action":"sts:AssumeRole"}]}' >/dev/null
  aws iam put-role-policy --role-name "$INSTANCE_ROLE" --policy-name collabforge-data --policy-document "{
    \"Version\":\"2012-10-17\",\"Statement\":[
      {\"Effect\":\"Allow\",\"Action\":[\"dynamodb:GetItem\",\"dynamodb:PutItem\",\"dynamodb:UpdateItem\",\"dynamodb:Query\",\"dynamodb:Scan\"],\"Resource\":\"arn:aws:dynamodb:$REGION:$ACCOUNT_ID:table/$DDB_TABLE\"},
      {\"Effect\":\"Allow\",\"Action\":[\"s3:GetObject\",\"s3:PutObject\",\"s3:DeleteObject\",\"s3:ListBucket\"],\"Resource\":[\"arn:aws:s3:::$MEDIA_BUCKET\",\"arn:aws:s3:::$MEDIA_BUCKET/*\"]}
    ]}"
  sleep 10
fi
ACCESS_ROLE_ARN="arn:aws:iam::$ACCOUNT_ID:role/$ACCESS_ROLE"
INSTANCE_ROLE_ARN="arn:aws:iam::$ACCOUNT_ID:role/$INSTANCE_ROLE"

echo "==> 6/11 Building container"
docker build -t "$ECR_REPO:latest" .

echo "==> 7/11 Pushing image"
aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com"
docker tag "$ECR_REPO:latest" "$ECR_URI:latest"
docker push "$ECR_URI:latest"

echo "==> 8/11 Preparing runtime environment (values not printed)"
ENV_FILE="backend/.env"
get() { grep -E "^$1=" "$ENV_FILE" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '\r'; }
RUNTIME_VARS=$(python - "$ENV_FILE" <<'PY'
import json, sys
keys = ["ANAKIN_API_KEY","OPENAI_API_KEY","GROQ_API_KEY","GEMINI_API_KEY","ELEVENLABS_API_KEY","YOUTUBE_API_KEY","NEWS_API_KEY"]
env = {}
try:
    for line in open(sys.argv[1]):
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            if k in keys and v:
                env[k] = v
except FileNotFoundError:
    pass
print(json.dumps(env))
PY
)
FRONTEND_ORIGIN="${FRONTEND_ORIGIN:-*pending*}"
RUNTIME_VARS=$(python - "$RUNTIME_VARS" "$REGION" "$MEDIA_BUCKET" "$DDB_TABLE" "$FRONTEND_ORIGIN" <<'PY'
import json, sys
env = json.loads(sys.argv[1])
env.update({
  "APP_ENV": "production", "PORT": "8080",
  "AWS_REGION": sys.argv[2], "AWS_S3_BUCKET": sys.argv[3],
  "AWS_DYNAMODB_TABLE": sys.argv[4], "DATABASE_MODE": "dynamodb",
  "FRONTEND_ORIGINS": sys.argv[5] if sys.argv[5] != "*pending*" else "http://localhost:3000",
})
print(json.dumps(env))
PY
)

echo "==> 9/11 Creating/updating App Runner service"
SERVICE_ARN=$(aws apprunner list-services --region "$REGION" \
  --query "ServiceSummaryList[?ServiceName=='$APP_NAME'].ServiceArn" --output text)
SOURCE_CFG=$(python - "$ECR_URI" "$ACCESS_ROLE_ARN" "$RUNTIME_VARS" <<'PY'
import json, sys
print(json.dumps({
  "ImageRepository": {
    "ImageIdentifier": sys.argv[1] + ":latest",
    "ImageRepositoryType": "ECR",
    "ImageConfiguration": {"Port": "8080", "RuntimeEnvironmentVariables": json.loads(sys.argv[3])},
  },
  "AuthenticationConfiguration": {"AccessRoleArn": sys.argv[2]},
  "AutoDeploymentsEnabled": False,
}))
PY
)
HEALTH_CFG='{"Protocol":"HTTP","Path":"/health","Interval":10,"Timeout":5,"HealthyThreshold":1,"UnhealthyThreshold":5}'
if [ -z "$SERVICE_ARN" ] || [ "$SERVICE_ARN" = "None" ]; then
  SERVICE_ARN=$(aws apprunner create-service --region "$REGION" \
    --service-name "$APP_NAME" \
    --source-configuration "$SOURCE_CFG" \
    --health-check-configuration "$HEALTH_CFG" \
    --instance-configuration "{\"Cpu\":\"1024\",\"Memory\":\"2048\",\"InstanceRoleArn\":\"$INSTANCE_ROLE_ARN\"}" \
    --query "Service.ServiceArn" --output text)
else
  aws apprunner update-service --region "$REGION" --service-arn "$SERVICE_ARN" \
    --source-configuration "$SOURCE_CFG" \
    --health-check-configuration "$HEALTH_CFG" \
    --instance-configuration "{\"Cpu\":\"1024\",\"Memory\":\"2048\",\"InstanceRoleArn\":\"$INSTANCE_ROLE_ARN\"}" >/dev/null
fi

echo "==> 10/11 Waiting for deployment"
for i in $(seq 1 60); do
  STATUS=$(aws apprunner describe-service --region "$REGION" --service-arn "$SERVICE_ARN" --query "Service.Status" --output text)
  echo "    status: $STATUS"
  [ "$STATUS" = "RUNNING" ] && break
  if [ "$STATUS" = "CREATE_FAILED" ] || [ "$STATUS" = "UPDATE_FAILED" ]; then
    echo "Deployment failed — check App Runner logs in CloudWatch"; exit 1
  fi
  sleep 15
done

SERVICE_URL="https://$(aws apprunner describe-service --region "$REGION" --service-arn "$SERVICE_ARN" --query "Service.ServiceUrl" --output text)"

echo "==> 11/11 Testing /health"
curl -fsS "$SERVICE_URL/health"
echo
echo "=================================================="
echo "Backend deployed: $SERVICE_URL"
echo "=================================================="
