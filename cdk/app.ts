#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as rds from 'aws-cdk-lib/aws-rds';
import { Construct } from 'constructs';

// Stack definition
class CostExplorerCloudStack extends cdk.Stack {
  constructor(scope: Construct, props?: cdk.StackProps) {
    super(scope, 'CostExplorerCloudStack', props);

    // Create a new VPC with a non-conflicting CIDR block.
    // The original VPC and database will be detached from the stack but retained in your account.
    const vpc = new ec2.Vpc(this, 'VPC2', { 
      ipAddresses: ec2.IpAddresses.cidr('10.1.0.0/16'),
      maxAzs: 2, 
      natGateways: 0,  // Remove NAT gateways to stay within free tier
      // Disable restricting the default security group to avoid permission issues.
      restrictDefaultSecurityGroup: false, 
      subnetConfiguration: [
        {
          cidrMask: 24,
          name: 'Public',
          subnetType: ec2.SubnetType.PUBLIC,
        }
      ]
    });

    // Create a new database instance in the new VPC.
    const database = new rds.DatabaseInstance(this, 'Database2', {
      engine: rds.DatabaseInstanceEngine.postgres({ version: rds.PostgresEngineVersion.VER_15_8 }),
      instanceType: ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.MICRO),
      vpc,
      vpcSubnets: {
        subnetType: ec2.SubnetType.PUBLIC,
      },
      credentials: rds.Credentials.fromGeneratedSecret('postgres'),
      databaseName: 'costexplorer',
      allocatedStorage: 20,
      storageType: rds.StorageType.GP2,
      backupRetention: cdk.Duration.days(0),
      deletionProtection: false,
      // The original database will be retained. You can change this new one to RETAIN later if you wish.
      removalPolicy: cdk.RemovalPolicy.DESTROY, 
      publiclyAccessible: true,
    });

    // Security Group for database access
    const dbSecurityGroup = new ec2.SecurityGroup(this, 'DatabaseSG', { 
      vpc, 
      allowAllOutbound: true,
      description: 'Security group for RDS database'
    });
    
    // Allow database access from anywhere (for development - restrict in production)
    dbSecurityGroup.addIngressRule(
      ec2.Peer.anyIpv4(), 
      ec2.Port.tcp(5432), 
      'Allow PostgreSQL access'
    );
    
    database.connections.allowDefaultPortFrom(dbSecurityGroup);

    // Outputs
    new cdk.CfnOutput(this, 'DatabaseEndpoint', { 
      value: database.instanceEndpoint.hostname,
      description: 'RDS PostgreSQL endpoint'
    });
    
    new cdk.CfnOutput(this, 'DatabaseSecret', { 
      value: database.secret?.secretArn || 'No secret',
      description: 'RDS secret ARN'
    });

    new cdk.CfnOutput(this, 'VpcId', {
      value: vpc.vpcId,
      description: 'VPC ID for the database'
    });

    new cdk.CfnOutput(this, 'DatabaseSecurityGroupId', {
      value: dbSecurityGroup.securityGroupId,
      description: 'Security Group ID for database access'
    });
  }
}

// App definition
const app = new cdk.App();
const stack = new CostExplorerCloudStack(app);

// Tag everything for cost tracking
cdk.Tags.of(stack).add('Project', 'CostExplorer');
cdk.Tags.of(stack).add('Environment', 'Development'); 