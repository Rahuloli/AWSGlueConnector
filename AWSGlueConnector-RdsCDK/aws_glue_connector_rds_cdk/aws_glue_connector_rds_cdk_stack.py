import os
from aws_cdk import (
    Stack,
    aws_ec2,
    aws_rds,
    aws_secretsmanager
)
import aws_cdk as core 
from constructs import Construct

class AwsGlueConnectorRdsCdkStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        rds_vpc, subnet_cidr = self.create_rdsvpc()
        
        # Creating Key Value Pair
        key_name = 'KeyPair-RDS-new'
        key_pair = aws_ec2.CfnKeyPair(
            self,'KeyPair-RDS',
            key_name = key_name
        )
        key_pair_name =  key_pair.key_name

        #Creating RDS Prerequisites
        
        rds_engine = aws_rds.DatabaseInstanceEngine.mysql(version=aws_rds.MysqlEngineVersion.VER_8_0_33)
        rds_instance = self.create_rds_prerequisites(rds_vpc,rds_engine)
    
    def create_rdsvpc(self):

        rds_vpc = aws_ec2.Vpc(
            self,
            "RDSVPC",
            ip_addresses= aws_ec2.IpAddresses.cidr('10.0.0.0/16'),
            max_azs = 2,
            enable_dns_hostnames=True,
            enable_dns_support=True,
            subnet_configuration=[
                aws_ec2.SubnetConfiguration(
            name="Public",
            subnet_type=aws_ec2.SubnetType.PUBLIC,
            cidr_mask=24
                ),
                aws_ec2.SubnetConfiguration(
            name="Private",
            subnet_type=aws_ec2.SubnetType.PRIVATE_WITH_EGRESS,
            cidr_mask= 24
                )
            ],
            nat_gateways=1
        )

        public_subnet = rds_vpc.public_subnets[0]
        subnet_cidr = public_subnet.ipv4_cidr_block
        public_nacl = aws_ec2.NetworkAcl(
            self,
            "RDSVPCPublicSubnetNACL",
            vpc = rds_vpc,
            subnet_selection=aws_ec2.SubnetSelection(subnets=[public_subnet])

        )

        #Adding default nacl rules

        public_nacl.add_entry(
            "PublicInboundRule",
            rule_number=100,
            traffic=aws_ec2.AclTraffic.all_traffic(),
            cidr = aws_ec2.AclCidr.ipv4("0.0.0.0/0"),
            direction=aws_ec2.TrafficDirection.INGRESS,
            rule_action=aws_ec2.Action.ALLOW
        )
        public_nacl.add_entry(
            "PublicOutboundRule",
            rule_number=100,
            traffic=aws_ec2.AclTraffic.all_traffic(),
            cidr = aws_ec2.AclCidr.ipv4("0.0.0.0/0"),
            direction=aws_ec2.TrafficDirection.EGRESS,
            rule_action=aws_ec2.Action.ALLOW
        )

        # Add Network ACL (NACL) for private subnet
        private_subnet = rds_vpc.private_subnets[0]
        private_nacl = aws_ec2.NetworkAcl(
            self,
            "RDSVPCPrivateSubnetNACL",
            vpc=rds_vpc,
            subnet_selection=aws_ec2.SubnetSelection(subnets=[private_subnet])
        )

        # Adding default NACL rules for the private subnet (customize as needed)
        private_nacl.add_entry(
            "PrivateInboundRule",
            rule_number=100,
            traffic=aws_ec2.AclTraffic.all_traffic(),
            cidr = aws_ec2.AclCidr.ipv4("10.0.128.0/17"),
            direction=aws_ec2.TrafficDirection.INGRESS,
            rule_action=aws_ec2.Action.ALLOW 
        )
        private_nacl.add_entry(
            "PrivateOutboundRule",
            rule_number=100,
            traffic=aws_ec2.AclTraffic.all_traffic(),
            cidr = aws_ec2.AclCidr.ipv4("0.0.0.0/0"),
            direction=aws_ec2.TrafficDirection.EGRESS,
            rule_action=aws_ec2.Action.ALLOW
        )

        return rds_vpc, subnet_cidr
    
    
    def create_rds_prerequisites(self, rds_vpc , rds_engine):
        
        security_group = aws_ec2.SecurityGroup(
            self,
            "RdsSecurityGroup",
            vpc = rds_vpc,
            description="Security Group for RDS Instance"
        )

        security_group.add_ingress_rule(
            aws_ec2.Peer.ipv4('10.0.0.0/16'),
            aws_ec2.Port.tcp(3306),

        )

        username = "user" + core.Fn.select(2,core.Fn.split('-',core.Fn.select(2,core.Fn.split('/', core.Aws.STACK_ID))))
        

        rds_secret = aws_secretsmanager.Secret(
        self,
        "RdsCredentialsSecret",
        secret_name="RdsCredentials",
        generate_secret_string=aws_secretsmanager.SecretStringGenerator(
        secret_string_template='{"username" :"'+ username +'","database": "MYSQLDatabase"}',
        exclude_characters="/@",
        password_length=16,
        generate_string_key="password"
        )
        )

        secret_value_password = rds_secret.secret_value_from_json("password")
       
        rds_instance = aws_rds.DatabaseInstance(
            self,
            "VerticaRDSInstance",
            engine = rds_engine,
            instance_type= aws_ec2.InstanceType.of(aws_ec2.InstanceClass.BURSTABLE2,aws_ec2.InstanceSize.MICRO),
            vpc = rds_vpc,
            vpc_subnets=aws_ec2.SubnetSelection(subnet_type=aws_ec2.SubnetType.PRIVATE_WITH_EGRESS),
            multi_az= True,
            removal_policy=core.RemovalPolicy.DESTROY,
            deletion_protection=False,
            publicly_accessible=True,
            cloudwatch_logs_exports=["error", "general", "slowquery"],
            security_groups=[security_group],
            database_name="MYSQL_Database",
            credentials=aws_rds.Credentials.from_username(username = username,password=secret_value_password)
           
        )
        
        return rds_instance