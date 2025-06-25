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

    // VPC - Simple setup for free tier
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

    // Database - Free tier friendly
    const database = new rds.DatabaseInstance(this, "Database", {
      engine: rds.DatabaseInstanceEngine.postgres({
        version: rds.PostgresEngineVersion.VER_15_8,
      }),
      instanceType: ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.MICRO), // Free tier
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
    });

    // ECR Repository
    const ecrRepository = new ecr.Repository(this, "AppRepository", {
      repositoryName: "cost-explorer-app",
      lifecycleRules: [
        {
          maxImageCount: 3,
        },
      ],
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // ECS Cluster with simple EC2 setup
    const cluster = new ecs.Cluster(this, "Cluster", {
      vpc,
      clusterName: "cost-explorer-cluster",
    });

    // Add EC2 capacity directly to cluster (simple approach)
    cluster.addCapacity("DefaultAutoScalingGroup", {
      instanceType: ec2.InstanceType.of(ec2.InstanceClass.T2, ec2.InstanceSize.MICRO), // Free tier
      minCapacity: 1,
      maxCapacity: 1,
      vpcSubnets: {
        subnetType: ec2.SubnetType.PUBLIC,
      },
    });

    // Simple task definition
    const taskDefinition = new ecs.Ec2TaskDefinition(this, "TaskDef");

    // Grant database access
    database.secret?.grantRead(taskDefinition.taskRole);

    // Container
    const container = taskDefinition.addContainer("app", {
      image: ecs.ContainerImage.fromEcrRepository(ecrRepository, "latest"),
      memoryReservationMiB: 256,
      environment: {
        NODE_ENV: "production",
        PORT: "3000",
      },
      secrets: database.secret
        ? {
            DB_HOST: ecs.Secret.fromSecretsManager(database.secret, "host"),
            DB_PORT: ecs.Secret.fromSecretsManager(database.secret, "port"),
            DB_USERNAME: ecs.Secret.fromSecretsManager(database.secret, "username"),
            DB_PASSWORD: ecs.Secret.fromSecretsManager(database.secret, "password"),
            DB_NAME: ecs.Secret.fromSecretsManager(database.secret, "dbname"),
          }
        : {},
      logging: ecs.LogDrivers.awsLogs({
        streamPrefix: "cost-explorer-app",
        logRetention: logs.RetentionDays.ONE_WEEK,
      }),
    });

    container.addPortMappings({
      containerPort: 3000,
      hostPort: 0, // Dynamic port
    });

    // Simple ECS service with load balancer
    const service = new ecsPatterns.ApplicationLoadBalancedEc2Service(
      this,
      "Service",
      {
        cluster,
        taskDefinition,
        publicLoadBalancer: true,
        desiredCount: 1,
        listenerPort: 80,
      }
    );

    // CloudFront for HTTPS
    const distribution = new cloudfront.Distribution(this, "Distribution", {
      defaultBehavior: {
        origin: new origins.LoadBalancerV2Origin(service.loadBalancer, {
          protocolPolicy: cloudfront.OriginProtocolPolicy.HTTP_ONLY,
          httpPort: 80,
        }),
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        allowedMethods: cloudfront.AllowedMethods.ALLOW_ALL,
        cachePolicy: cloudfront.CachePolicy.CACHING_DISABLED,
        originRequestPolicy: cloudfront.OriginRequestPolicy.ALL_VIEWER,
      },
      priceClass: cloudfront.PriceClass.PRICE_CLASS_100,
      comment: "Cost Explorer Cloud Distribution",
    });

    // Allow ECS to connect to database
    database.connections.allowDefaultPortFrom(service.service);

    // Allow external connections to database (for development/testing)
    // WARNING: This allows connections from anywhere - restrict IP range for production
    database.connections.allowFrom(
      ec2.Peer.anyIpv4(),
      ec2.Port.tcp(5432),
      "Allow PostgreSQL connections from anywhere"
    );

    // Outputs
    new cdk.CfnOutput(this, "DatabaseEndpoint", {
      value: database.instanceEndpoint.hostname,
      description: "Database endpoint",
    });

    new cdk.CfnOutput(this, "DatabaseSecret", {
      value: database.secret?.secretArn || "No secret",
      description: "Database secret ARN",
    });

    new cdk.CfnOutput(this, "ECRRepository", {
      value: ecrRepository.repositoryUri,
      description: "ECR repository URI",
    });

    new cdk.CfnOutput(this, "LoadBalancerURL", {
      value: `http://${service.loadBalancer.loadBalancerDnsName}`,
      description: "Application URL (HTTP)",
    });

    new cdk.CfnOutput(this, "CloudFrontURL", {
      value: `https://${distribution.distributionDomainName}`,
      description: "Application URL (HTTPS)",
    });
  }
}

// App definition
const app = new cdk.App();
const stack = new CostExplorerCloudStack(app);

// Simple tags
cdk.Tags.of(stack).add("Project", "CostExplorer");

app.synth();
