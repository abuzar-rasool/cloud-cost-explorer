#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as rds from 'aws-cdk-lib/aws-rds';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';

// Stack definition
class CostExplorerCloudStack extends cdk.Stack {
  constructor(scope: Construct, props?: cdk.StackProps) {
    super(scope, 'CostExplorerCloudStack', props);

    // VPC
    const vpc = new ec2.Vpc(this, 'VPC', { maxAzs: 2, natGateways: 0 });

    // Database
    const database = new rds.DatabaseInstance(this, 'Database', {
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
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      publiclyAccessible: true,
    });

    // EC2 Security Group
    const sg = new ec2.SecurityGroup(this, 'SG', { vpc, allowAllOutbound: true });
    [22, 80, 443, 3000].forEach(port => sg.addIngressRule(ec2.Peer.anyIpv4(), ec2.Port.tcp(port)));
    database.connections.allowDefaultPortFrom(sg);
    
    // Allow database access from your local machine (for DB viewer)
    database.connections.allowDefaultPortFrom(ec2.Peer.anyIpv4()); // For PoC - allow from anywhere

    // EC2 Role
    const role = new iam.Role(this, 'Role', {
      assumedBy: new iam.ServicePrincipal('ec2.amazonaws.com'),
      managedPolicies: [iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonSSMManagedInstanceCore')],
    });
    database.secret?.grantRead(role);

    // User data
    const userData = ec2.UserData.forLinux();
    userData.addCommands(
      'yum update -y && yum install -y docker git',
      'systemctl start docker && systemctl enable docker',
      'usermod -a -G docker ec2-user',
      'curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose',
      'chmod +x /usr/local/bin/docker-compose',
      'mkdir -p /home/ec2-user/app && chown ec2-user:ec2-user /home/ec2-user/app',
      `echo "DATABASE_URL=postgresql://postgres:\${$(aws secretsmanager get-secret-value --secret-id ${database.secret?.secretArn} --query SecretString --output text | jq -r .password)}@${database.instanceEndpoint.hostname}:5432/costexplorer" > /home/ec2-user/.env`
    );

    // EC2 Instance
    const instance = new ec2.Instance(this, 'Instance', {
      vpc,
      vpcSubnets: {
        subnetType: ec2.SubnetType.PUBLIC,
      },
      instanceType: ec2.InstanceType.of(ec2.InstanceClass.T2, ec2.InstanceSize.MICRO),
      machineImage: ec2.MachineImage.latestAmazonLinux2023(),
      securityGroup: sg,
      role,
      userData,
    });

    // Outputs
    new cdk.CfnOutput(this, 'DatabaseEndpoint', { value: database.instanceEndpoint.hostname });
    new cdk.CfnOutput(this, 'DatabaseSecret', { value: database.secret?.secretArn || 'No secret' });
    new cdk.CfnOutput(this, 'EC2PublicIP', { value: instance.instancePublicIp });
    new cdk.CfnOutput(this, 'SSH', { value: `ssh ec2-user@${instance.instancePublicIp}` });
  }
}

// App definition
const app = new cdk.App();
const stack = new CostExplorerCloudStack(app);

// Tag everything for cost tracking
cdk.Tags.of(stack).add('Project', 'CostExplorer');
cdk.Tags.of(stack).add('Environment', 'Development'); 