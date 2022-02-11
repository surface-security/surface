import * as ec2 from '@aws-cdk/aws-ec2';
import * as rds from '@aws-cdk/aws-rds';
import * as ecs from '@aws-cdk/aws-ecs';
import * as asm from '@aws-cdk/aws-secretsmanager';
import * as elbv2 from '@aws-cdk/aws-elasticloadbalancingv2';
import * as cdk from '@aws-cdk/core';

export class SurfStack extends cdk.Stack {
  constructor(scope: cdk.App, id: string, props?: cdk.StackProps) {
    super(scope, id, props);
    const vpc = new ec2.Vpc(this, 'SURFVPC', {
        cidr: "10.0.0.0/22",
        subnetConfiguration: [
          {
            cidrMask: 28,
            name: 'egress',
            subnetType: ec2.SubnetType.PUBLIC,
          },
          {
            cidrMask: 28,
            name: 'app',
            subnetType: ec2.SubnetType.PRIVATE_WITH_NAT,
          },
          {
            cidrMask: 28,
            name: 'rds',
            subnetType: ec2.SubnetType.PRIVATE_ISOLATED,
          }
        ]
    })
    const instance = new rds.DatabaseInstance(this, 'Instance', {
      engine: rds.DatabaseInstanceEngine.mysql({ version: rds.MysqlEngineVersion.VER_8_0_23 }),
      instanceType: ec2.InstanceType.of(ec2.InstanceClass.T2, ec2.InstanceSize.MICRO),
      credentials: rds.Credentials.fromGeneratedSecret('syscdk'), // Optional - will default to 'admin' username and generated password
      allocatedStorage: 20,
      databaseName: 'surface',
      backupRetention: cdk.Duration.days(0),
      vpc,
      vpcSubnets: {
        subnetType: ec2.SubnetType.PRIVATE_ISOLATED,        
      }
    });
    instance.connections.allowDefaultPortFromAnyIpv4()  //... on the isolated subnet!

    const cluster = new ecs.Cluster(this, 'SURFCluster', { vpc });
    const taskDefinition = new ecs.TaskDefinition(this, 'TD', {
      memoryMiB: '2048',
      cpu: '1024',
      compatibility: ecs.Compatibility.FARGATE,
    });
    
    const djangoSecret = new asm.Secret(this, 'DjangoSecret', {
      generateSecretString: {
        // same length as django.core.management.utils.get_random_secret_key
        passwordLength: 50,
      },
    });
    const container = taskDefinition.addContainer('SURFWeb', {
      image: ecs.ContainerImage.fromAsset('../..', {file: 'dev/Dockerfile'}),
      memoryLimitMiB: 2048,
      command: ['./manage.py', 'runserver', '0.0.0.0:8000'],
      environment: {
        SURF_ALLOWED_HOSTS: '*',
        SURF_DATABASE_URL: `mysql://${instance.dbInstanceEndpointAddress}:${instance.dbInstanceEndpointPort}/surface`,
        SURF_DEBUG: 'false'
      },
      secrets: {
        SURF_DATABASE_USER: ecs.Secret.fromSecretsManager(instance.secret as asm.ISecret, 'username'),
        SURF_DATABASE_PASSWORD: ecs.Secret.fromSecretsManager(instance.secret as asm.ISecret, 'password'),
        SURF_SECRET_KEY: ecs.Secret.fromSecretsManager(djangoSecret),
      },
      logging: ecs.LogDriver.awsLogs({'streamPrefix': 'surf'}),
    });
    container.addPortMappings({
      containerPort: 8000,
    });

    const service = new ecs.FargateService(this, 'Service', {
      cluster,
      taskDefinition,
      enableExecuteCommand: true,
    });

    const lb = new elbv2.ApplicationLoadBalancer(this, 'LB', { vpc, internetFacing: true });
    const listener = lb.addListener('Listener', { port: 80 });
    service.registerLoadBalancerTargets(
      {
        containerName: 'SURFWeb',
        containerPort: 8000,
        newTargetGroupId: 'ECS',
        listener: ecs.ListenerConfig.applicationListener(listener, {
          protocol: elbv2.ApplicationProtocol.HTTP,
          // FIXME: get a decent healthcheck endpoint
          healthCheck: {healthyHttpCodes: '302'},
        }),
      },
    );

    new cdk.CfnOutput(this, 'lbDNSRecord', {
      value: lb.loadBalancerDnsName,
      description: 'LB DNS Record - set your CNAME to this',
    });
  }
}
