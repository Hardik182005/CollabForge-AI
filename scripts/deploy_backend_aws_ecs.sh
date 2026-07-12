#!/usr/bin/env bash
# CollabForge AI — backend on ECS Fargate + ALB.
# Fallback used when the AWS account is not subscribed for App Runner
# (SubscriptionRequiredException). Same container image, same env handling.
set -euo pipefail
# Git Bash on Windows: stop MSYS mangling /paths in AWS CLI args
export MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL="*"

CLUSTER="collabforge"
SERVICE="collabforge-backend"
TASK_FAMILY="collabforge-backend"
ECR_REPO="collabforge-backend"
ALB_NAME="collabforge-alb"
TG_NAME="collabforge-tg"
DDB_TABLE="${DDB_TABLE:-collabforge-campaigns}"
MEDIA_BUCKET_PREFIX="${MEDIA_BUCKET_PREFIX:-collabforge-media}"

echo "==> Identity"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="${AWS_REGION:-$(aws configure get region)}"
ECR_URI="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$ECR_REPO"
MEDIA_BUCKET="$MEDIA_BUCKET_PREFIX-$ACCOUNT_ID"
echo "    account=$ACCOUNT_ID region=$REGION"

echo "==> Network (default VPC)"
VPC_ID=$(aws ec2 describe-vpcs --filters Name=isDefault,Values=true --query "Vpcs[0].VpcId" --output text)
SUBNETS=$(aws ec2 describe-subnets --filters Name=vpc-id,Values=$VPC_ID --query "Subnets[].SubnetId" --output text | tr '\t' ' ')
SUBNET_ARGS=$(echo $SUBNETS | tr ' ' ',')

SG_ID=$(aws ec2 describe-security-groups --filters Name=group-name,Values=collabforge-sg Name=vpc-id,Values=$VPC_ID --query "SecurityGroups[0].GroupId" --output text 2>/dev/null)
if [ "$SG_ID" = "None" ] || [ -z "$SG_ID" ]; then
  SG_ID=$(aws ec2 create-security-group --group-name collabforge-sg --description "CollabForge backend" --vpc-id "$VPC_ID" --query GroupId --output text)
  aws ec2 authorize-security-group-ingress --group-id "$SG_ID" --protocol tcp --port 80 --cidr 0.0.0.0/0 >/dev/null
  aws ec2 authorize-security-group-ingress --group-id "$SG_ID" --protocol tcp --port 8080 --cidr 0.0.0.0/0 >/dev/null
fi

echo "==> IAM roles"
EXEC_ROLE="collabforge-ecs-exec"
if ! aws iam get-role --role-name "$EXEC_ROLE" >/dev/null 2>&1; then
  aws iam create-role --role-name "$EXEC_ROLE" --assume-role-policy-document '{
    "Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"ecs-tasks.amazonaws.com"},"Action":"sts:AssumeRole"}]}' >/dev/null
  aws iam attach-role-policy --role-name "$EXEC_ROLE" --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
  sleep 8
fi
TASK_ROLE="collabforge-ecs-task"
if ! aws iam get-role --role-name "$TASK_ROLE" >/dev/null 2>&1; then
  aws iam create-role --role-name "$TASK_ROLE" --assume-role-policy-document '{
    "Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"ecs-tasks.amazonaws.com"},"Action":"sts:AssumeRole"}]}' >/dev/null
  aws iam put-role-policy --role-name "$TASK_ROLE" --policy-name collabforge-data --policy-document "{
    \"Version\":\"2012-10-17\",\"Statement\":[
      {\"Effect\":\"Allow\",\"Action\":[\"dynamodb:GetItem\",\"dynamodb:PutItem\",\"dynamodb:UpdateItem\",\"dynamodb:Query\",\"dynamodb:Scan\"],\"Resource\":\"arn:aws:dynamodb:$REGION:$ACCOUNT_ID:table/$DDB_TABLE\"},
      {\"Effect\":\"Allow\",\"Action\":[\"s3:GetObject\",\"s3:PutObject\",\"s3:DeleteObject\",\"s3:ListBucket\"],\"Resource\":[\"arn:aws:s3:::$MEDIA_BUCKET\",\"arn:aws:s3:::$MEDIA_BUCKET/*\"]}
    ]}"
  sleep 8
fi

echo "==> ALB + target group"
ALB_ARN=$(aws elbv2 describe-load-balancers --names "$ALB_NAME" --query "LoadBalancers[0].LoadBalancerArn" --output text 2>/dev/null || true)
if [ -z "$ALB_ARN" ] || [ "$ALB_ARN" = "None" ]; then
  ALB_ARN=$(aws elbv2 create-load-balancer --name "$ALB_NAME" --type application \
    --subnets $SUBNETS --security-groups "$SG_ID" \
    --query "LoadBalancers[0].LoadBalancerArn" --output text)
fi
ALB_DNS=$(aws elbv2 describe-load-balancers --load-balancer-arns "$ALB_ARN" --query "LoadBalancers[0].DNSName" --output text)

TG_ARN=$(aws elbv2 describe-target-groups --names "$TG_NAME" --query "TargetGroups[0].TargetGroupArn" --output text 2>/dev/null || true)
if [ -z "$TG_ARN" ] || [ "$TG_ARN" = "None" ]; then
  TG_ARN=$(aws elbv2 create-target-group --name "$TG_NAME" --protocol HTTP --port 8080 \
    --vpc-id "$VPC_ID" --target-type ip \
    --health-check-path /health --health-check-interval-seconds 30 \
    --query "TargetGroups[0].TargetGroupArn" --output text)
fi
LISTENER=$(aws elbv2 describe-listeners --load-balancer-arn "$ALB_ARN" --query "Listeners[0].ListenerArn" --output text 2>/dev/null || true)
if [ -z "$LISTENER" ] || [ "$LISTENER" = "None" ]; then
  aws elbv2 create-listener --load-balancer-arn "$ALB_ARN" --protocol HTTP --port 80 \
    --default-actions Type=forward,TargetGroupArn=$TG_ARN >/dev/null
fi

echo "==> CloudWatch log group"
aws logs create-log-group --log-group-name /ecs/collabforge-backend 2>/dev/null || true

echo "==> Task definition (env from backend/.env — values not printed)"
CONTAINER_ENV=$(python - "backend/.env" "$REGION" "$MEDIA_BUCKET" "$DDB_TABLE" "${FRONTEND_ORIGIN:-http://localhost:3000}" <<'PY'
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
env.update({
  "APP_ENV": "production", "PORT": "8080",
  "AWS_REGION": sys.argv[2], "AWS_S3_BUCKET": sys.argv[3],
  "AWS_DYNAMODB_TABLE": sys.argv[4], "DATABASE_MODE": "dynamodb",
  "FRONTEND_ORIGINS": sys.argv[5],
})
print(json.dumps([{"name": k, "value": v} for k, v in env.items()]))
PY
)
echo "==> ECR repo + build + push image (:latest)"
aws ecr describe-repositories --repository-names "$ECR_REPO" >/dev/null 2>&1 \
  || aws ecr create-repository --repository-name "$ECR_REPO" >/dev/null
aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com"
docker build -t "$ECR_URI:latest" -f Dockerfile .
docker push "$ECR_URI:latest"

TASK_DEF=$(python - "$ECR_URI" "$CONTAINER_ENV" "$ACCOUNT_ID" "$REGION" "$EXEC_ROLE" "$TASK_ROLE" <<'PY'
import json, sys
print(json.dumps({
  "family": "collabforge-backend",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512", "memory": "1024",
  "executionRoleArn": f"arn:aws:iam::{sys.argv[3]}:role/{sys.argv[5]}",
  "taskRoleArn": f"arn:aws:iam::{sys.argv[3]}:role/{sys.argv[6]}",
  "containerDefinitions": [{
    "name": "backend",
    "image": sys.argv[1] + ":latest",
    "portMappings": [{"containerPort": 8080, "protocol": "tcp"}],
    "environment": json.loads(sys.argv[2]),
    "logConfiguration": {"logDriver": "awslogs", "options": {
      "awslogs-group": "/ecs/collabforge-backend",
      "awslogs-region": sys.argv[4],
      "awslogs-stream-prefix": "backend"}},
  }],
}))
PY
)
aws ecs register-task-definition --cli-input-json "$TASK_DEF" >/dev/null

echo "==> Cluster + service"
aws ecs describe-clusters --clusters "$CLUSTER" --query "clusters[0].status" --output text 2>/dev/null | grep -q ACTIVE \
  || aws ecs create-cluster --cluster-name "$CLUSTER" >/dev/null

if aws ecs describe-services --cluster "$CLUSTER" --services "$SERVICE" --query "services[0].status" --output text 2>/dev/null | grep -q ACTIVE; then
  aws ecs update-service --cluster "$CLUSTER" --service "$SERVICE" \
    --task-definition "$TASK_FAMILY" --force-new-deployment >/dev/null
else
  aws ecs create-service --cluster "$CLUSTER" --service-name "$SERVICE" \
    --task-definition "$TASK_FAMILY" --desired-count 1 --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[${SUBNET_ARGS// /,}],securityGroups=[$SG_ID],assignPublicIp=ENABLED}" \
    --load-balancers "targetGroupArn=$TG_ARN,containerName=backend,containerPort=8080" >/dev/null
fi

echo "==> Waiting for service to stabilize"
aws ecs wait services-stable --cluster "$CLUSTER" --services "$SERVICE"

echo "==> Testing /health via ALB"
for i in $(seq 1 20); do
  if curl -fsS -m 10 "http://$ALB_DNS/health"; then echo; break; fi
  sleep 10
done

echo "=================================================="
echo "Backend deployed (HTTP behind ALB): http://$ALB_DNS"
echo "Front it with CloudFront for HTTPS (deploy_frontend_aws.sh does this)."
echo "=================================================="
