# Cost Explorer Cloud - Ultra Simple CDK

**One file. No build step. Just deploy.**

## 🚀 Super Quick Deploy

```bash
cd cdk
npm install
npx cdk bootstrap  # First time only
npx cdk deploy
```

## 📁 Project Structure

```
cdk/
├── app.ts          # Everything is here!
├── package.json    # Dependencies
└── cdk.json        # CDK config
```

## 🏗️ What Gets Created

- VPC with 2 public subnets
- PostgreSQL Database (t3.micro, 20GB)
- EC2 Instance (t2.micro) with Docker
- Security Groups (ports 22, 80, 443, 3000)
- IAM Role for database access

## 💰 Free Tier Eligible

- EC2: 750 hours/month of t2.micro
- RDS: 750 hours/month of t3.micro  
- Storage: 20GB included

## 📋 Prerequisites

1. AWS CLI configured (`aws configure`)
2. Node.js 18+
3. AdministratorAccess IAM permissions

## 🔧 After Deployment

### Get Database Password
```bash
aws secretsmanager get-secret-value --secret-id <SECRET_ARN> --query SecretString --output text | jq -r .password
```

### SSH to EC2
```bash
ssh ec2-user@<EC2_PUBLIC_IP>
```

### Deploy Your App
```bash
# On EC2:
cd /home/ec2-user/app
git clone https://github.com/your-username/your-app.git
cd your-app
docker-compose up -d
```

## 🗑️ Cleanup

```bash
npx cdk destroy
```

## 🛠️ Customize

Just edit `app.ts` - everything is in one file!

**Want to change the region?** Edit line 70 in `app.ts`

**Want different ports?** Edit line 30 in `app.ts`

**Want different instance sizes?** Edit lines 18 & 47 in `app.ts`

## 🔒 Security Note

This setup opens common ports to the internet. For production:
- Restrict security groups to your IP only
- Use private subnets with NAT Gateway
- Enable database backups

## 📊 Monitor Costs

Check your AWS Free Tier usage in the AWS Console under Billing & Cost Management. 