#!/usr/bin/env python3
import os

import aws_cdk as cdk

from aws_glue_connector_rds_cdk.aws_glue_connector_rds_cdk_stack import AwsGlueConnectorRdsCdkStack


app = cdk.App()
print ('Creating environment')
cdk_env = cdk.Environment(account='076913533062', region='us-east-1')
AwsGlueConnectorRdsCdkStack(app, "AwsGlueConnectorRdsCdkStack",env = cdk_env)

app.synth()
