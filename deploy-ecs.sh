#!/bin/bash

set -e

echo "🚀 Cost Explorer Cloud - ECS Deployment Script"
echo "=============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if AWS CLI is configured
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo -e "${RED}❌ AWS CLI not configured. Please run 'aws configure' first.${NC}"
    exit 1
fi

# Get AWS account ID and region
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=$(aws configure get region || echo "us-east-1")

echo -e "${BLUE}📋 Using AWS Account: ${AWS_ACCOUNT_ID}${NC}"
echo -e "${BLUE}📋 Using AWS Region: ${AWS_REGION}${NC}"

# Navigate to CDK directory
cd cdk

echo -e "${YELLOW}📦 Installing CDK dependencies...${NC}"
npm install

echo -e "${YELLOW}🔨 Bootstrapping CDK (if needed)...${NC}"
npx cdk bootstrap aws://${AWS_ACCOUNT_ID}/${AWS_REGION}

echo -e "${YELLOW}🏗️  Deploying infrastructure...${NC}"
npx cdk deploy --require-approval never

echo -e "${GREEN}✅ Infrastructure deployed successfully!${NC}"

# Get ECR repository URI from CDK outputs
ECR_URI=$(aws cloudformation describe-stacks \
    --stack-name CostExplorerCloudStack \
    --query 'Stacks[0].Outputs[?OutputKey==`ECRRepository`].OutputValue' \
    --output text)

if [ -z "$ECR_URI" ]; then
    echo -e "${RED}❌ Could not get ECR repository URI from stack outputs${NC}"
    exit 1
fi

echo -e "${BLUE}📦 ECR Repository: ${ECR_URI}${NC}"

# Navigate back to root and build/push Docker image
cd ..

echo -e "${YELLOW}🔐 Logging into ECR...${NC}"
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_URI}

echo -e "${YELLOW}🐳 Building Docker image...${NC}"
docker buildx build --platform linux/amd64 -t cost-explorer-app ./app

echo -e "${YELLOW}🏷️  Tagging image...${NC}"
docker tag cost-explorer-app:latest ${ECR_URI}:latest

echo -e "${YELLOW}📤 Pushing image to ECR...${NC}"
docker push ${ECR_URI}:latest

echo -e "${YELLOW}🔄 Forcing ECS service update...${NC}"
# Get the actual service name from the cluster
SERVICE_NAME=$(aws ecs list-services \
    --cluster cost-explorer-cluster \
    --region ${AWS_REGION} \
    --query 'serviceArns[0]' \
    --output text | cut -d'/' -f3 2>/dev/null || echo "")

if [ ! -z "$SERVICE_NAME" ]; then
    aws ecs update-service \
        --cluster cost-explorer-cluster \
        --service ${SERVICE_NAME} \
        --force-new-deployment \
        --region ${AWS_REGION} > /dev/null && echo "Service update initiated"
else
    echo "No service found in cluster - this is normal for first deployment"
fi

echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
echo ""
echo -e "${BLUE}📋 Stack Outputs:${NC}"
aws cloudformation describe-stacks \
    --stack-name CostExplorerCloudStack \
    --query 'Stacks[0].Outputs[?OutputKey!=`ECRPushCommands`].[OutputKey,OutputValue,Description]' \
    --output table

echo ""
echo -e "${GREEN}🎉 Your application is deploying! It may take a few minutes to be fully available.${NC}"

# Get CloudFront URL from stack outputs
CLOUDFRONT_URL=$(aws cloudformation describe-stacks \
    --stack-name CostExplorerCloudStack \
    --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontURL`].OutputValue' \
    --output text 2>/dev/null || echo "")

if [ ! -z "$CLOUDFRONT_URL" ]; then
    echo ""
    echo -e "${GREEN}🌐 Your app is available at:${NC}"
    echo -e "${BLUE}   ${CLOUDFRONT_URL}${NC}"
else
    echo -e "${YELLOW}💡 Use the LoadBalancerURL from the outputs above to access your application.${NC}"
fi 