# Cloud Cost Explorer

A comprehensive cloud cost analysis platform that collects, processes, and visualizes pricing data from major cloud providers (AWS, Azure, GCP). The application provides detailed cost comparisons, regional pricing analysis, and storage optimization insights to help organizations make informed cloud infrastructure decisions.

## 🏗️ Project Architecture

The application is designed with a modern, scalable architecture:

### **Frontend (Next.js)**

- **Location**: `/app` - React-based web application
- **Features**: Interactive dashboards, cost comparison tables, regional pricing graphs
- **Tech Stack**: Next.js 14, TypeScript, Tailwind CSS, React Query
- **Components**: Provider comparison cards, cost charts, storage analysis tools

### **Backend Infrastructure (AWS CDK)**

- **Location**: `/cdk` - Infrastructure as Code
- **Services**: ECS, RDS PostgreSQL, ECR, CloudFront, Application Load Balancer
- **Deployment**: Automated via `deploy-ecs.sh` script
- **Free Tier Optimized**: Uses t3.micro RDS and t2.micro EC2 instances

### **Database (PostgreSQL + Prisma)**

- **Location**: `/prisma` - Database schema and ORM
- **Tables**:
  - `on-demand-vm-pricing`: Virtual machine pricing data
  - `storage-pricing`: Storage service pricing data
- **Features**: Type-safe database access, automatic migrations

### **Data Pipeline (Python)**

- **Location**: `/scripts` - Data collection and processing
- **Providers**: AWS, Azure (GCP in development)
- **Output**: Standardized CSV format for consistent analysis
- **Automation**: Manual triggers with comprehensive logging

## 🚀 Quick Start

### Prerequisites

- **AWS CLI** configured with appropriate permissions
- **Docker** and Docker Compose (for local development)
- **Python 3.10+** (for data pipeline)
- **Node.js 18+** (for frontend and CDK)
- **PostgreSQL 15+** (if running database elsewhere)

### 1. Local Development Setup

#### Database Setup

```bash
# Start PostgreSQL database using Docker
docker-compose up -d

# Set database connection (for local development)
export DATABASE_URL=postgresql://clouduser:cloudpassword@localhost:5432/cloudcosts
```

#### Frontend Application

```bash
# Navigate to app directory
cd app

# Install dependencies
npm install

# Generate Prisma client
npx prisma generate

# Set up database schema
npx prisma db push

# Start development server
npm run dev
```

The application will be available at `http://localhost:3000`

#### Data Pipeline Setup

```bash
# Install Python dependencies
pip install -r requirements.txt

# Set up database schema
python setup_db.py

# Run data collection pipeline
python run_pipeline.py
```

### 2. Production Deployment

#### Automated Deployment (Recommended)

```bash
# Run the deployment script
./deploy-ecs.sh
```

This script will:

- Deploy AWS infrastructure using CDK
- Build and push Docker image to ECR
- Deploy application to ECS
- Configure CloudFront for HTTPS
- Output application URLs

#### Manual Deployment

```bash
# Deploy infrastructure
cd cdk
npm install
npx cdk bootstrap  # First time only
npx cdk deploy

# Build and deploy application
cd ..
docker buildx build --platform linux/amd64 -t cost-explorer-app ./app
docker tag cost-explorer-app:latest <ECR_URI>:latest
docker push <ECR_URI>:latest
```

## 📊 Data Pipeline

### Overview

The data pipeline collects pricing information from cloud providers and stores it in a standardized format for analysis.

### Manual Execution

```bash
# Run complete pipeline (all providers)
python run_pipeline.py

# Run specific providers
python run_pipeline.py --providers aws,azure

# Run with custom database connection
python run_pipeline.py --db-url postgresql://user:pass@host:5432/db
```

### Pipeline Components

- **AWS Data Collection**: EC2 instance pricing, S3 storage pricing
- **Azure Data Collection**: VM pricing, Blob storage pricing
- **Data Processing**: Standardization, region mapping, price validation
- **Database Storage**: Automated schema updates, data insertion

### Output Files

- `data/aws_ondemand_vm_pricing_YYYYMMDD_HHMMSS.csv`
- `data/aws_s3_storage_pricing_YYYYMMDD_HHMMSS.csv`
- `data/azure_instances.csv`
- `data/azure_storage_pricing_service_per_row.csv`

## 🏗️ Infrastructure Details

### AWS CDK Stack (`/cdk`)

The infrastructure is defined in a single `app.ts` file for simplicity:

#### Core Components

- **VPC**: Public subnets across 2 availability zones
- **RDS PostgreSQL**: t3.micro instance (free tier eligible)
- **ECS Cluster**: EC2-based with t2.micro instances
- **ECR Repository**: Container image storage
- **Application Load Balancer**: HTTP traffic distribution
- **CloudFront**: HTTPS termination and global distribution
- **Secrets Manager**: Database credentials management

#### Free Tier Optimization

- Uses t3.micro for RDS (750 hours/month)
- Uses t2.micro for ECS (750 hours/month)
- 20GB storage included
- No NAT gateways (cost optimization)

#### Security Features

- Database credentials in Secrets Manager
- Security groups for controlled access
- CloudFront for HTTPS termination
- IAM roles for service permissions

### Deployment Script (`deploy-ecs.sh`)

Automated deployment script that handles:

- CDK infrastructure deployment
- Docker image building and pushing
- ECS service updates
- CloudFront distribution setup
- Output URL generation

## 📋 Database Schema

### Prisma Models (`/prisma`)

#### OnDemandVMPricing

```prisma
model OnDemandVMPricing {
  id                  Int      @id @default(autoincrement())
  vm_name             String
  provider_name       Provider
  virtual_cpu_count   Int
  memory_gb           Float
  cpu_arch            String
  price_per_hour_usd  Float
  gpu_count           Int
  gpu_name            String?
  gpu_memory          Float
  os_type             OS_Type
  region              Region
  other_details       Json?
  createdAt           DateTime @default(now())
  updatedAt           DateTime @updatedAt

  @@map("on-demand-vm-pricing")
}
```

#### StoragePricing

```prisma
model StoragePricing {
  id                Int          @id @default(autoincrement())
  provider_name     Provider
  service_name      String
  storage_class     String
  region            Region
  access_tier       Access_Tiers
  capacity_price    Float?
  read_price        Float?
  write_price       Float?
  flat_item_price   Float?
  other_details     Json?
  createdAt         DateTime     @default(now())
  updatedAt         DateTime     @updatedAt

  @@map("storage-pricing")
}
```

## 📊 Standardized Data Formats

The data collection scripts for each cloud provider (AWS, Azure, and eventually GCP) are designed to produce CSV files with standardized formats. This allows for consistent processing and analysis across all providers.

### Standardized CSV Output Format For Compute Instances

Please note: We only add OnDemand instances.

The CSV file has the following columns:

| Field Name           | Data Type     | Description                                                                                                                                                                      | Example (for a GCP instance) |
| -------------------- | ------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------- |
| `vm_name`            | String        | The official name/type of the VM instance (e.g., instance name type).                                                                                                            | `"n2-standard-2"`            |
| `provider_name`      | String        | The name of the cloud provider. This will be one of `AWS`, `AZURE`, or `GCP`.                                                                                                    | `"GCP"`                      |
| `virtual_cpu_count`  | Integer       | The number of virtual CPUs (vCPUs) for the instance.                                                                                                                             | `2`                          |
| `memory_gb`          | Float         | The amount of memory (RAM) for the instance, specified in Gibibytes (GiB).                                                                                                       | `8.0`                        |
| `cpu_arch`           | String        | The CPU architecture. Common values are `"x86_64"` and `"ARM64"`.                                                                                                                | `"x86_64"`                   |
| `price_per_hour_usd` | Float         | The on-demand (pay-as-you-go) price for the instance per hour, in US Dollars.                                                                                                    | `0.095`                      |
| `gpu_count`          | Integer       | The number of GPUs attached to the instance. Should be `0` if none.                                                                                                              | `1`                          |
| `gpu_name`           | String        | The name or model of the attached GPU (e.g., "NVIDIA Tesla T4"). Should be empty or null if `gpu_count` is 0.                                                                    | `"NVIDIA Tesla T4"`          |
| `gpu_memory`         | Float         | The total memory for all GPUs attached, in Gibibytes (GiB). Should be `0.0` if `gpu_count` is 0.                                                                                 | `16.0`                       |
| `os_type`            | String (Enum) | The general operating system family. Possible values are: `LINUX`, `WINDOWS`, `OTHER`.                                                                                           | `"LINUX"`                    |
| `region`             | String (Enum) | The geographical continent where the instance is located. Possible values are: `north_america`, `south_america`, `europe`, `asia`, `africa`, `oceania`, `antarctica`.            | `"north_america"`            |
| `other_details`      | String (JSON) | A single JSON string containing provider-specific details. In the output CSV, this entire string is enclosed in double quotes (`"`), and any internal double quotes are escaped. | `"{""key"":""value""}"`      |

### Standardized CSV Output Format For Storage

Please note: We only add OnDemand/Consumption pricing.

The CSV file has the following columns:

| Field Name        | Data Type     | Description                                                                                                                                                                      | Example (for an AWS S3 instance) |
| ----------------- | ------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------- |
| `provider_name`   | String        | The name of the cloud provider. This will be one of `AWS`, `AZURE`, or `GCP`.                                                                                                    | `"AWS"`                          |
| `service_name`    | String        | The name of the storage service (e.g., "S3", "Blob Storage", "Cloud Storage").                                                                                                   | `"S3"`                           |
| `storage_class`   | String        | The storage class/tier name (e.g., "Standard", "Infrequent Access", "Archive").                                                                                                  | `"Standard"`                     |
| `region`          | String (Enum) | The geographical continent where the storage is located. Possible values are: `north_america`, `south_america`, `europe`, `asia`, `africa`, `oceania`, `antarctica`.             | `"north_america"`                |
| `access_tier`     | String (Enum) | The access tier classification. Possible values are: `hot`, `cool`, `archive`, `deep_archive`.                                                                                   | `"hot"`                          |
| `capacity_price`  | Float         | The price per GB per month for storage capacity, in US Dollars. Should be `null` if not applicable.                                                                              | `0.023`                          |
| `read_price`      | Float         | The price per 1,000 read operations, in US Dollars. Should be `null` if not applicable.                                                                                          | `0.0004`                         |
| `write_price`     | Float         | The price per 1,000 write operations, in US Dollars. Should be `null` if not applicable.                                                                                         | `0.005`                          |
| `flat_item_price` | Float         | Any flat monthly fee or item-based pricing, in US Dollars. Should be `null` if not applicable.                                                                                   | `0.50`                           |
| `other_details`   | String (JSON) | A single JSON string containing provider-specific details. In the output CSV, this entire string is enclosed in double quotes (`"`), and any internal double quotes are escaped. | `"{""key"":""value""}"`          |

## 🔧 Configuration

### Environment Variables

```

```
