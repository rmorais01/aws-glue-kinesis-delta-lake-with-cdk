#!/usr/bin/env python3
import os

import aws_cdk as cdk

from cdk_stacks import (
  DeltalakeConnectionStack,
  KdsStack,
  GlueJobRoleStack,
  GlueStreamDataSchemaStack,
  GlueDeltaLakeSchemaStack,
  GlueStreamingJobStack,
  DataLakePermissionsStack,
  S3BucketStack
)

APP_ENV = cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'),
  region=os.getenv('CDK_DEFAULT_REGION'))


app = cdk.App()

#deltalake_conn = DeltalakeConnectionStack(app, 'GlueDeltaLakeConnection')

s3_bucket = S3BucketStack(app, 'DeltaLakeS3Path')
#s3_bucket.add_dependency(deltalake_conn)

kds_stack = KdsStack(app, 'KinesisStreamAsGlueStreamingJobDataSource')
kds_stack.add_dependency(s3_bucket)

glue_deltalake_schema = GlueDeltaLakeSchemaStack(app, 'GlueSchemaOnDeltaLake')
glue_deltalake_schema.add_dependency(kds_stack)

glue_job_role = GlueJobRoleStack(app, 'GlueStreamingSinkToDeltaLakeJobRole')
glue_job_role.add_dependency(glue_deltalake_schema)

grant_lf_permissions_on_glue_job_role = DataLakePermissionsStack(app, 'GrantLFPermissionsOnGlueJobRole',
  glue_job_role.iam_role
)
grant_lf_permissions_on_glue_job_role.add_dependency(glue_job_role)

glue_streaming_job = GlueStreamingJobStack(app, 'GlueStreamingSinkToDeltaLake',
  glue_job_role.iam_role,
  kds_stack.kinesis_stream
)
glue_streaming_job.add_dependency(grant_lf_permissions_on_glue_job_role)

app.synth()
