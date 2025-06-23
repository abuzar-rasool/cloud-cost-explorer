#!/usr/bin/env node
import * as cdk from "aws-cdk-lib";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import * as rds from "aws-cdk-lib/aws-rds";
import * as ecs from "aws-cdk-lib/aws-ecs";
import * as ecsPatterns from "aws-cdk-lib/aws-ecs-patterns";
import * as ecr from "aws-cdk-lib/aws-ecr";
import * as logs from "aws-cdk-lib/aws-logs";

import * as cloudfront from "aws-cdk-lib/aws-cloudfront";
import * as origins from "aws-cdk-lib/aws-cloudfront-origins";

import { Construct } from "constructs";

// Stack definition
class CostExplorerCloudStack extends cdk.Stack {
  constructor(scope: Construct, props?: cdk.StackProps) {
    super(scope, "CostExplorerCloudStack", props);

    // VPC - Same as your previous setup, free tier friendly
    const vpc = new ec2.Vpc(this, "VPC", {
      maxAzs: 2,
      natGateways: 0, // Free tier: no NAT gateways
      subnetConfiguration: [
        {
          name: "public",
          subnetType: ec2.SubnetType.PUBLIC,
          cidrMask: 24,
        },
      ],
    });

    // Security Group for Database
    const dbSecurityGroup = new ec2.SecurityGroup(this, "DatabaseSG", {
      vpc,
      description: "Security group for RDS database",
      allowAllOutbound: true,
    });

    // Database - Similar to your previous setup but optimized for free tier
    const database = new rds.DatabaseInstance(this, "Database", {
      engine: rds.DatabaseInstanceEngine.postgres({
        version: rds.PostgresEngineVersion.VER_15_8,
      }),
      instanceType: ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.MICRO), // Free tier: t3.micro
      vpc,
      vpcSubnets: {
        subnetType: ec2.SubnetType.PUBLIC,
      },
      credentials: rds.Credentials.fromGeneratedSecret("postgres"),
      databaseName: "costexplorer",
      allocatedStorage: 20, // Free tier: up to 20 GB
      storageType: rds.StorageType.GP2,
      backupRetention: cdk.Duration.days(0), // Free tier: 0 days backup
      deletionProtection: false,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      publiclyAccessible: true,
      securityGroups: [dbSecurityGroup],
    });

    // ECR Repository for Docker images
    const ecrRepository = new ecr.Repository(this, "AppRepository", {
      repositoryName: "cost-explorer-app",
      lifecycleRules: [
        {
          maxImageCount: 3, // Keep only 3 images to stay within free tier limits
        },
      ],
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // ECS Cluster
    const cluster = new ecs.Cluster(this, "Cluster", {
      vpc,
      clusterName: "cost-explorer-cluster",
    });

    // Task Definition
    const taskDefinition = new ecs.FargateTaskDefinition(this, "TaskDef", {
      memoryLimitMiB: 512, // Free tier: up to 512 MB
      cpu: 256, // Free tier: up to 0.25 vCPU
    });

    // Grant the task definition access to read the database secret
    database.secret?.grantRead(taskDefinition.taskRole);

    // Container Definition
    const container = taskDefinition.addContainer("app", {
      image: ecs.ContainerImage.fromEcrRepository(ecrRepository, "latest"),
      environment: {
        NODE_ENV: "production",
        PORT: "3000",
      },
      secrets: database.secret
        ? {
            DB_HOST: ecs.Secret.fromSecretsManager(database.secret, "host"),
            DB_PORT: ecs.Secret.fromSecretsManager(database.secret, "port"),
            DB_USERNAME: ecs.Secret.fromSecretsManager(
              database.secret,
              "username"
            ),
            DB_PASSWORD: ecs.Secret.fromSecretsManager(
              database.secret,
              "password"
            ),
            DB_NAME: ecs.Secret.fromSecretsManager(database.secret, "dbname"),
          }
        : {},
      logging: ecs.LogDrivers.awsLogs({
        streamPrefix: "cost-explorer-app",
        logRetention: logs.RetentionDays.ONE_WEEK, // Free tier friendly
      }),
    });

    container.addPortMappings({
      containerPort: 3000,
      protocol: ecs.Protocol.TCP,
    });

    // Fargate Service with Application Load Balancer
    const fargateService =
      new ecsPatterns.ApplicationLoadBalancedFargateService(
        this,
        "FargateService",
        {
          cluster,
          taskDefinition,
          publicLoadBalancer: true,
          desiredCount: 1, // Free tier: single instance
          listenerPort: 80,
          platformVersion: ecs.FargatePlatformVersion.LATEST,
          assignPublicIp: true, // Required since we're using public subnets only
        }
      );

    // CloudFront will handle HTTPS termination, so we keep ALB on HTTP only
    // This is more cost-effective and simpler for the free tier

    // CloudFront Distribution for custom subdomain and better performance
    const distribution = new cloudfront.Distribution(this, "Distribution", {
      defaultBehavior: {
        origin: new origins.LoadBalancerV2Origin(fargateService.loadBalancer, {
          protocolPolicy: cloudfront.OriginProtocolPolicy.HTTP_ONLY, // ALB will handle HTTPS internally
          httpPort: 80,
        }),
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        allowedMethods: cloudfront.AllowedMethods.ALLOW_ALL,
        cachePolicy: cloudfront.CachePolicy.CACHING_DISABLED, // Disable caching for dynamic content
        originRequestPolicy: cloudfront.OriginRequestPolicy.ALL_VIEWER,
      },
      priceClass: cloudfront.PriceClass.PRICE_CLASS_100, // Cheapest option
      comment: "Cost Explorer Cloud Distribution",
    });

    // Allow ECS to connect to the database
    database.connections.allowDefaultPortFrom(fargateService.service);

    // Allow database access from anywhere (for DB viewers/debugging)
    database.connections.allowDefaultPortFrom(ec2.Peer.anyIpv4());

    // Scale down to 0 during off-hours (optional cost optimization)
    const scalableTarget = fargateService.service.autoScaleTaskCount({
      minCapacity: 0, 
      maxCapacity: 2, 
    });


    // Outputs
    new cdk.CfnOutput(this, "DatabaseEndpoint", {
      value: database.instanceEndpoint.hostname,
      description: "RDS PostgreSQL endpoint",
    });

    new cdk.CfnOutput(this, "DatabaseSecret", {
      value: database.secret?.secretArn || "No secret",
      description: "RDS secret ARN for database credentials",
    });

    new cdk.CfnOutput(this, "ECRRepository", {
      value: ecrRepository.repositoryUri,
      description: "ECR repository URI for Docker images",
    });

    new cdk.CfnOutput(this, "LoadBalancerURL", {
      value: `http://${fargateService.loadBalancer.loadBalancerDnsName}`,
      description: "Application Load Balancer URL (HTTP)",
    });

    new cdk.CfnOutput(this, "LoadBalancerHTTPSURL", {
      value: `https://${fargateService.loadBalancer.loadBalancerDnsName}`,
      description: "Application Load Balancer URL (HTTPS)",
    });

    new cdk.CfnOutput(this, "CloudFrontURL", {
      value: `https://${distribution.distributionDomainName}`,
      description: "CloudFront Distribution URL (Custom Domain with HTTPS)",
    });

    new cdk.CfnOutput(this, "ECRPushCommands", {
      value: [
        `aws ecr get-login-password --region ${this.region} | docker login --username AWS --password-stdin ${ecrRepository.repositoryUri}`,
        `docker build -t cost-explorer-app ./app`,
        `docker tag cost-explorer-app:latest ${ecrRepository.repositoryUri}:latest`,
        `docker push ${ecrRepository.repositoryUri}:latest`,
      ].join(" && "),
      description: "Commands to build and push Docker image to ECR",
    });
  }
}

// App definition
const app = new cdk.App();
const stack = new CostExplorerCloudStack(app);

// Tag everything for cost tracking
cdk.Tags.of(stack).add("Project", "CostExplorer");
cdk.Tags.of(stack).add("Environment", "Development");

app.synth();
