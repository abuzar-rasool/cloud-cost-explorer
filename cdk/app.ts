#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as rds from 'aws-cdk-lib/aws-rds';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as amplify from '@aws-cdk/aws-amplify-alpha';
import * as codebuild from 'aws-cdk-lib/aws-codebuild';
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

    // Create GitHub source code provider (requires GitHub token in Secrets Manager)
    const sourceCodeProvider = new amplify.GitHubSourceCodeProvider({
      owner: 'abuzar-rasool',
      repository: 'cloud-cost-explorer',
      oauthToken: cdk.SecretValue.secretsManager('github-oauth-token'),
    });

    // Create Amplify App for Next.js hosting
    const amplifyApp = new amplify.App(this, 'CostExplorerApp', {
      appName: 'cloud-cost-explorer',
      description: 'Cost Explorer Cloud Application',
      sourceCodeProvider: sourceCodeProvider,
      platform: amplify.Platform.WEB_COMPUTE, // Enable SSR for Next.js
      environmentVariables: {
        DATABASE_URL: `postgresql://postgres:\${aws_secretsmanager.get_secret_value(${database.secret?.secretArn}).password}@${database.instanceEndpoint.hostname}:5432/costexplorer`,
        NEXT_PUBLIC_DATABASE_HOST: database.instanceEndpoint.hostname,
        NODE_ENV: 'production',
      },
      buildSpec: codebuild.BuildSpec.fromObjectToYaml({
        version: '1.0',
        applications: [
          {
            appRoot: 'app', // Your Next.js app is in the @/app directory
            frontend: {
              phases: {
                preBuild: {
                  commands: [
                    'node --version',
                    'npm --version',
                    'npm ci',
                  ],
                },
                build: {
                  commands: [
                    'npm run build',
                  ],
                },
              },
              artifacts: {
                baseDirectory: '.next',
                files: ['**/*'],
              },
              cache: {
                paths: ['node_modules/**/*'],
              },
            },
          },
        ],
      }),
      // Custom rules for Next.js SPA routing
      customRules: [
        {
          source: '/<*>',
          target: '/index.html',
          status: amplify.RedirectStatus.NOT_FOUND_REWRITE,
        },
      ],
      // Auto branch deletion to manage resources
      autoBranchDeletion: true,
    });

    // Add main branch for production
    const mainBranch = amplifyApp.addBranch('main', {
      stage: 'PRODUCTION',
      autoBuild: true,
      environmentVariables: {
        DATABASE_URL: `postgresql://postgres:\${aws_secretsmanager.get_secret_value(${database.secret?.secretArn}).password}@${database.instanceEndpoint.hostname}:5432/costexplorer`,
      },
    });

    // Create IAM role for Amplify to access database secrets
    const amplifyRole = new iam.Role(this, 'AmplifyServiceRole', {
      assumedBy: new iam.ServicePrincipal('amplify.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('AdministratorAccess-Amplify'),
      ],
      inlinePolicies: {
        SecretsManagerAccess: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: [
                'secretsmanager:GetSecretValue',
                'secretsmanager:DescribeSecret',
              ],
              resources: [database.secret?.secretArn || '*'],
            }),
          ],
        }),
      },
    });

    // Note: IAM role attachment will be done manually in the Amplify console
    // The alpha CDK construct doesn't fully support automatic role attachment yet

    // Outputs
    new cdk.CfnOutput(this, 'DatabaseEndpoint', { 
      value: database.instanceEndpoint.hostname,
      description: 'RDS PostgreSQL endpoint'
    });
    
    new cdk.CfnOutput(this, 'DatabaseSecret', { 
      value: database.secret?.secretArn || 'No secret',
      description: 'RDS secret ARN'
    });
    
    new cdk.CfnOutput(this, 'AmplifyAppId', { 
      value: amplifyApp.appId,
      description: 'Amplify App ID'
    });
    
    new cdk.CfnOutput(this, 'AmplifyURL', { 
      value: `https://main.${amplifyApp.defaultDomain}`,
      description: 'Amplify App URL'
    });

    new cdk.CfnOutput(this, 'GitHubSetupInstructions', {
      value: 'Create a GitHub personal access token with repo permissions and store it in AWS Secrets Manager with the name "github-oauth-token"',
      description: 'GitHub setup instructions'
    });

    new cdk.CfnOutput(this, 'AmplifyRoleArn', {
      value: amplifyRole.roleArn,
      description: 'Amplify service role ARN (attach manually in Amplify console)'
    });
  }
}

// App definition
const app = new cdk.App();
const stack = new CostExplorerCloudStack(app);

// Tag everything for cost tracking
cdk.Tags.of(stack).add('Project', 'CostExplorer');
cdk.Tags.of(stack).add('Environment', 'Development'); 