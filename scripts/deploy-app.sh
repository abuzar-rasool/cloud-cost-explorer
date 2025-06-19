#!/bin/bash

# Cost Explorer App Deployment Script (App Runner)
# This script builds the Docker image and deploys it to AWS App Runner

set -e

echo "🚀 Starting deployment process..."

# Get the AWS account ID and region
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=$(aws configure get region)

if [ -z "$AWS_REGION" ]; then
    AWS_REGION="us-east-1"
    echo "⚠️  No region configured, defaulting to us-east-1"
fi

echo "📋 AWS Account: $AWS_ACCOUNT_ID"
echo "📋 AWS Region: $AWS_REGION"

# ECR repository details
ECR_REPOSITORY="cost-explorer-app"
ECR_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY"

echo "🏗️  Building Docker image..."
cd app
docker build -t $ECR_REPOSITORY:latest .

echo "🔐 Logging into ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_URI

echo "🏷️  Tagging image..."
docker tag $ECR_REPOSITORY:latest $ECR_URI:latest

echo "📤 Pushing image to ECR..."
docker push $ECR_URI:latest

echo "🔄 Starting App Runner deployment..."
aws apprunner start-deployment \
    --service-arn $(aws apprunner list-services --query "ServiceSummaryList[?ServiceName=='cost-explorer-app'].ServiceArn" --output text) \
    --region $AWS_REGION

echo "✅ Deployment initiated!"
echo "🌐 Your app will be available at the App Runner URL from the CDK outputs"
echo "📊 Check deployment status: aws apprunner describe-service --service-arn \$(aws apprunner list-services --query \"ServiceSummaryList[?ServiceName=='cost-explorer-app'].ServiceArn\" --output text) --region $AWS_REGION"

cd .. 