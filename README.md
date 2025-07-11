
# AWS Glue Streaming ETL Job and Delta Lake Sample Project with CDK

![glue-streaming-data-to-deltalake-table](./glue-streaming-data-to-deltalake-table.svg)

In this project, we create a streaming ETL job in AWS Glue to integrate [Delta Lake](https://docs.delta.io/latest/index.html) with a streaming data from kinesis.


This project can be deployed with [AWS CDK Python](https://docs.aws.amazon.com/cdk/api/v2/).

The `cdk.json` file tells the CDK Toolkit how to execute your app.

This project is set up like a standard Python project.  The initialization
process also creates a virtualenv within this project, stored under the `.venv`
directory.  To create the virtualenv it assumes that there is a `python3`
(or `python` for Windows) executable in your path with access to the `venv`
package. If for any reason the automatic creation of the virtualenv fails,
you can create the virtualenv manually.

To manually create a virtualenv on MacOS and Linux:

```
$ python3 -m venv .venv
```

After the init process completes and the virtualenv is created, you can use the following
step to activate your virtualenv.

```
$ source .venv/bin/activate
```

Once the virtualenv is activated, you can install the required dependencies.

```
(.venv) $ pip install -r requirements.txt
```

Update the cdk context configuration file accordingly, `cdk.context.json`.

For example:
<pre>
{
  "kinesis_stream_name": "deltalake-demo-stream",
  "glue_assets_s3_bucket_name": "aws-glue-assets-rm-demo",
  "glue_job_script_file_name": "spark_kinesis_to_deltalake_publisher.py",
  "glue_job_name": "streaming_data_from_kds_into_deltalake_table",
  "glue_job_input_arguments": {
    "--catalog": "spark_catalog",
    "--database_name": "deltalake_db",
    "--table_name": "products",
    "--primary_key": "product_id",
    "--partition_key": "category",
    "--kinesis_database_name": "deltalake_stream_db",
    "--kinesis_table_name": "kinesis_stream_table",
    "--starting_position_of_kinesis_iterator": "LATEST",
    "--delta_s3_path": "s3://glue-deltalake-rm-demo-us-east-1/deltalake_db/products",
    "--aws_region": "us-east-1",
    "--window_size": "100 seconds",
    "--user-jars-first": "true"
  }
}
</pre>

At this point you can now synthesize the CloudFormation template for this code.

<pre>
(.venv) $ export CDK_DEFAULT_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
(.venv) $ export CDK_DEFAULT_REGION=$(aws configure get region)
(.venv) $ cdk synth --all
</pre>

To add additional dependencies, for example other CDK libraries, just add
them to your `setup.py` file and rerun the `pip install -r requirements.txt`
command.

## Run Test

1. Create a S3 bucket for Delta Lake table
   <pre>
   (.venv) $ cdk deploy DeltaLakeS3Path
   </pre>
2. Create a Kinesis data stream
   <pre>
   (.venv) $ cdk deploy KinesisStreamAsGlueStreamingJobDataSource
   </pre>
3. Define a schema for the streaming data
   <pre>
   (.venv) $ cdk deploy GlueSchemaOnKinesisStream
   </pre>

4. Create Database in Glue Data Catalog for Delta Lake table
   <pre>
   (.venv) $ cdk deploy GlueSchemaOnDeltaLake
   </pre>
5. Create Glue Streaming Job

   * (step 1) Select Glue Job Scripts and upload into S3

     **List of Glue Job Scirpts**
     | File name | Spark Writes |
     |-----------|--------------|
     | spark_deltalake_writes_with_dataframe.py | DataFrame append |

     <pre>
     (.venv) $ ls src/main/python/
      spark_deltalake_writes_with_dataframe.py
     (.venv) $ aws s3 mb <i>s3://aws-glue-assets-rm-demo</i> --region <i>us-east-1</i>
     (.venv) $ aws s3 cp src/main/python/spark_deltalake_writes_with_dataframe.py <i>s3://aws-glue-assets-rm-demo/scripts/</i>
     </pre>

   * (step 2) Provision the Glue Streaming Job

     <pre>
     (.venv) $ cdk deploy GlueStreamingSinkToDeltaLakeJobRole \
                          GrantLFPermissionsOnGlueJobRole \
                          GlueStreamingSinkToDeltaLake
     </pre>

6.  Run glue job to load data from Kinesis Data Streams into S3
    <pre>
    (.venv) $ aws glue start-job-run --job-name <i>streaming_data_from_kds_into_deltalake_table</i>
    </pre>
7. Generate streaming data

    We can synthetically generate data in JSON format using a simple Python application.
    <pre>
    (.venv) $ python src/utils/gen_fake_kinesis_stream_data.py \
               --region-name <i>us-east-1</i> \
               --stream-name <i>your-stream-name</i> \
               --console \
               --max-count 10
    </pre>

## Clean Up

1. Stop the glue job by replacing the job name in below command.

   <pre>
   (.venv) $ JOB_RUN_IDS=$(aws glue get-job-runs \
              --job-name streaming_data_from_kds_into_deltalake_table | jq -r '.JobRuns[] | select(.JobRunState=="RUNNING") | .Id' \
              | xargs)
   (.venv) $ aws glue batch-stop-job-run \
              --job-name streaming_data_from_kds_into_deltalake_table \
              --job-run-ids $JOB_RUN_IDS
   </pre>

2. Delete the CloudFormation stack by running the below command.

   <pre>
   (.venv) $ cdk destroy --all
   </pre>

## References
AWS Samples
