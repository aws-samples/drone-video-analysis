import * as cdk from 'aws-cdk-lib';
import {Construct} from 'constructs';
import * as s3 from 'aws-cdk-lib/aws-s3';
import {BucketProps} from "aws-cdk-lib/aws-s3";
import {
    CloudFormationInit, InitCommand, InitConfig, InitElement,
    InitFile,
    InitPackage, InitService, InitUser,
    InstanceClass,
    InstanceSize,
    InstanceType
} from "aws-cdk-lib/aws-ec2";
import {InitPlatform} from "aws-cdk-lib/aws-ec2/lib/private/cfn-init-internal";
import * as path from "path";
import * as fs from "fs";
import {ManagedPolicy} from "aws-cdk-lib/aws-iam";
import {S3EventSource} from "aws-cdk-lib/aws-lambda-event-sources";

const defaultBucketProps: BucketProps = {
    autoDeleteObjects: true,
    removalPolicy: cdk.RemovalPolicy.DESTROY,
}

export class CdkStack extends cdk.Stack {
    constructor(scope: Construct, id: string, props?: cdk.StackProps) {
        super(scope, id, props);

        // Frames bucket
        const framesBucket = new s3.Bucket(this, 'FramesBucket', {...defaultBucketProps})

        // KVS stream
        const kinesisVideoStream = new cdk.aws_kinesisvideo.CfnStream(this, 'kinesis-video-stream', {
            dataRetentionInHours: cdk.Duration.days(200).toHours(),
        })

        // Create a vpc and elastic IP
        const vpc = new cdk.aws_ec2.Vpc(this, 'network-vpc', {});

        const eip = new cdk.aws_ec2.CfnEIP(this, 'ec2-proxy-static-ip', {});

        // create an ec2 instance with a public IP
        // new ssh keypair
        const keypair = new cdk.aws_ec2.CfnKeyPair(this, 'ssh-keypair', {
            keyName: this.stackName + '-rtsp-server-keypair',
        })

        // new security group that opens up port 22, 1935 and 8080, 9997
        //  22 for ssh, 1935 for rtmp, 8080 for http, 9997 for rtsp-server-http-api
        const allowPortsOpen = [22, 1935, 8080, 9997];
        const securityGroup = new cdk.aws_ec2.SecurityGroup(this, 'security-group', {
            vpc: vpc,
            allowAllOutbound: true,
        })
        allowPortsOpen.forEach(port => {
            securityGroup.addIngressRule(cdk.aws_ec2.Peer.anyIpv4(), cdk.aws_ec2.Port.tcp(port), `allow port ${port} open`)
        })


        const rootVolume = cdk.aws_ec2.BlockDeviceVolume.ebs(100, {
            deleteOnTermination: true,
        });

        // get relative path to current directory
        const rtspProxyCodeDirectory = path.join(__dirname, '..', 'rtsp-proxy-code');
        // list all files and map them to a cfn-init file
        const rtspProxyCodeFiles = fs.readdirSync(rtspProxyCodeDirectory).map(file => {
            return InitFile.fromFileInline(`/home/ec2-user/rtsp-proxy-code/${file}`,
                `${rtspProxyCodeDirectory}/${file}`);
        })


        const instanceTypeLarge = InstanceType.of(InstanceClass.T3, InstanceSize.XLARGE);
        // const chosenKeyPair = backupKeypair;
        const chosenKeyPair = keypair;
        const streamServer = new cdk.aws_ec2.Instance(this, `stream-server`, {
            vpc: vpc,
            instanceType: instanceTypeLarge,
            machineImage: cdk.aws_ec2.MachineImage.latestAmazonLinux({}),
            keyName: chosenKeyPair.keyName,
            securityGroup: securityGroup,
            vpcSubnets: {
                subnetType: cdk.aws_ec2.SubnetType.PUBLIC,
            },
            blockDevices: [
                {
                    deviceName: '/dev/xvda',
                    volume: rootVolume,
                }
            ],

            /*
            * # Install and start the docker engine
            *
                sudo yum install docker git -y
                sudo service docker start
                sudo usermod -a -G docker ec2-user
                sudo chkconfig docker on

                # Setup the docker-compose
                sudo curl -L https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m) -o /usr/local/bin/docker-compose
                sudo chmod +x /usr/local/bin/docker-compose
                mv /usr/local/bin/docker-compose /bin/docker-compose
            * */

            init: CloudFormationInit.fromElements(
                // Update the instance
                InitCommand.shellCommand('sudo yum update -y'),
                InitCommand.shellCommand('sudo yum install git docker jq -y'),
                InitCommand.shellCommand('sudo service docker start'),
                InitCommand.shellCommand('sudo usermod -a -G docker ec2-user'),
                //     Install docker compose
                InitCommand.shellCommand('sudo curl -L https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m) -o /usr/local/bin/docker-compose'),
                InitCommand.shellCommand('sudo chmod +x /usr/local/bin/docker-compose'),
                InitCommand.shellCommand('mv /usr/local/bin/docker-compose /bin/docker-compose'),
                // Code files
                ...rtspProxyCodeFiles,
            ),

        });


        // allow session manager to connect to the instance streamServer
        streamServer.connections.allowFromAnyIpv4(cdk.aws_ec2.Port.tcp(22), 'allow ssh from anywhere')
        streamServer.connections.allowFromAnyIpv4(cdk.aws_ec2.Port.tcp(1935), 'allow rtmp from anywhere')
        streamServer.connections.allowFromAnyIpv4(cdk.aws_ec2.Port.tcp(8080), 'allow custom http from anywhere')
        streamServer.connections.allowFromAnyIpv4(cdk.aws_ec2.Port.tcp(9997), 'allow rtsp-server-http-api from anywhere')


        // Associate the elastic IP with the instance
        new cdk.aws_ec2.CfnEIPAssociation(this, 'static-ip-association', {
            eip: eip.ref,
            instanceId: streamServer.instanceId,
        });


        // Grant access to the ec2 role for kinesis video stream and s3 frames bucket
        const kinesisVideoStreamPolicy = new cdk.aws_iam.PolicyStatement({
            effect: cdk.aws_iam.Effect.ALLOW,
            actions: [
                'kinesisvideo:*',
            ],
            resources: ["*"],
        });

        if (streamServer.role) {
            streamServer.role.addToPrincipalPolicy(kinesisVideoStreamPolicy);
            framesBucket.grantWrite(streamServer.role);
            // add full s3 access to the role as it can write to the frames bucket created by user
            streamServer.role
                .addManagedPolicy(cdk.aws_iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonS3FullAccess'));
        }

        // new sns topic and notification
        const snsTopic = new cdk.aws_sns.Topic(this, 'sns-topic', {});

        const frameAnalysisLambda = new cdk.aws_lambda.Function(this, 'frame-analysis-lambda', {
            runtime: cdk.aws_lambda.Runtime.PYTHON_3_8,
            handler: 's3-frame-analysis-trigger.handler',
            code: cdk.aws_lambda.Code.fromAsset(path.join(__dirname, '..', 'lambda')),
        })

        // create a trigger for the lambda for the frames bucket
        frameAnalysisLambda.addEventSource(new S3EventSource(framesBucket, {
            events: [s3.EventType.OBJECT_CREATED],
            filters: [{suffix: ".jpg"}]
        }))

        // CfnOuput public ip of the stream server
        new cdk.CfnOutput(this, 'stream-server-public-ip', {
            value: streamServer.instancePublicIp,
        })

        new cdk.CfnOutput(this, 'stream-name', {
            value: kinesisVideoStream.attrArn
        })

    }


}
