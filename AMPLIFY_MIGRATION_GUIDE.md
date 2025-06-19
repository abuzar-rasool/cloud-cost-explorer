# AWS Amplify Migration Guide: EC2 to Amplify Hosting

## Overview
This guide helps you migrate your cost-explorer-cloud application from EC2-based hosting to AWS Amplify hosting, maintaining your PostgreSQL database while leveraging Amplify's managed hosting capabilities.

## Prerequisites

### 1. GitHub Setup
1. Create a GitHub Personal Access Token:
   - Go to GitHub Settings > Developer settings > Personal access tokens > Tokens (classic)
   - Click "Generate new token (classic)"
   - Select scopes: `repo` (Full control of private repositories)
   - Copy the token (you won't see it again)

2. Store the token in AWS Secrets Manager:
   ```bash
   aws secretsmanager create-secret \
     --name "github-oauth-token" \
     --description "GitHub OAuth token for Amplify" \
     --secret-string "your-github-token-here"
   ```

### 2. Environment Variables
Set these environment variables before deploying:
```bash
export GITHUB_OWNER="your-github-username"
export GITHUB_REPO="cost-explorer-cloud"
```

## What Changed in Your Infrastructure

### Removed Components:
- ✅ EC2 instance and related resources
- ✅ EC2 security group
- ✅ EC2 IAM role and instance profile
- ✅ User data scripts
- ✅ NAT gateways (cost optimization)

### Added Components:
- ✅ AWS Amplify App with Next.js support
- ✅ GitHub integration with OAuth
- ✅ Amplify IAM role with database access
- ✅ Environment variables for database connection
- ✅ Build configuration for Next.js app in `app/` directory

### Preserved Components:
- ✅ PostgreSQL RDS database (no changes)
- ✅ VPC and networking (optimized for cost)
- ✅ Database security group and credentials

## Deployment Steps

### 1. Install Dependencies
```bash
cd cdk
npm install
```

### 2. Set Environment Variables
```bash
export GITHUB_OWNER="abuzar"
export GITHUB_REPO="cost-explorer-cloud"
```

### 3. Store GitHub Token in Secrets Manager
```bash
aws secretsmanager create-secret \
  --name "github-oauth-token" \
  --description "GitHub OAuth token for Amplify" \
  --secret-string "ghp_your_actual_token_here"
```

### 4. Deploy Infrastructure
```bash
npm run deploy
```

### 5. Configure Your Next.js App
Update your `app/` directory to include database connection configuration:

```typescript
// app/lib/db.ts
const DATABASE_URL = process.env.DATABASE_URL || 
  `postgresql://postgres:${process.env.DB_PASSWORD}@${process.env.NEXT_PUBLIC_DATABASE_HOST}:5432/costexplorer`;

// Use this for your database connections
```

## Cost Optimization Features

### Free Tier Compliance:
- ✅ RDS t3.micro instance (750 hours/month free)
- ✅ No NAT gateways (saves ~$45/month)
- ✅ Amplify free tier: 1000 build minutes/month, 15GB served/month
- ✅ Public subnets only (no NAT gateway costs)

### Resource Management:
- ✅ Auto branch deletion enabled
- ✅ Minimal IAM permissions
- ✅ No EBS volumes or additional storage

## Monitoring and Management

### Amplify Console:
- Access your app at: `https://main.{app-id}.amplifyapp.com`
- View build logs and deployment status
- Manage environment variables
- Configure custom domains

### Database Access:
- Database endpoint: Available in CDK outputs
- Credentials: Stored in AWS Secrets Manager
- Connection: Via environment variables in Amplify

## Troubleshooting

### Common Issues:

1. **GitHub Token Issues:**
   ```bash
   # Update the token
   aws secretsmanager update-secret \
     --secret-id "github-oauth-token" \
     --secret-string "new-token-here"
   ```

2. **Build Failures:**
   - Check that your `app/package.json` has correct build scripts
   - Verify Node.js version compatibility
   - Check Amplify build logs in the console

3. **Database Connection:**
   - Ensure database is publicly accessible
   - Verify security group rules
   - Check environment variables in Amplify

### Useful Commands:
```bash
# Check CDK diff
npm run diff

# View all Amplify apps
aws amplify list-apps

# Get build status
aws amplify list-jobs --app-id {your-app-id} --branch-name main

# View database secret
aws secretsmanager get-secret-value --secret-id {secret-arn}
```

## Next Steps

1. **Deploy the infrastructure** using the steps above
2. **Test your application** at the Amplify URL
3. **Configure custom domain** (optional) in Amplify Console
4. **Set up monitoring** and alerts as needed
5. **Update DNS** if migrating from existing domain

## Cost Comparison

### Before (EC2):
- EC2 t2.micro: ~$8.50/month (after free tier)
- NAT Gateway: ~$45/month
- EBS storage: ~$2/month
- **Total: ~$55.50/month**

### After (Amplify):
- Amplify hosting: Free tier (up to limits)
- RDS t3.micro: Free tier (750 hours)
- No NAT Gateway: $0
- **Total: ~$0-5/month** (within free tier limits)

Your migration to AWS Amplify will significantly reduce costs while providing better scalability and developer experience! 