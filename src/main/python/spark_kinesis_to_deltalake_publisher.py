#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os
import sys
import re

from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue import DynamicFrame

from pyspark.conf import SparkConf
from pyspark.sql import DataFrame, Row
from pyspark.sql.types import *
from pyspark.sql.functions import *


def get_kinesis_stream_name_from_arn(stream_arn):
  ARN_PATTERN = re.compile(r'arn:aws:kinesis:([a-z0-9-]+):(\d+):stream/([a-zA-Z0-9-_]+)')
  results = ARN_PATTERN.match(stream_arn)
  return results.group(3)

args = getResolvedOptions(sys.argv, ['JOB_NAME',
  'catalog',
  'database_name',
  'table_name',
  'partition_key',
  'kinesis_stream_arn',
  'starting_position_of_kinesis_iterator',
  'delta_s3_path',
  'aws_region',
  'window_size'
])

CATALOG = args['catalog']

DELTA_S3_PATH = args['delta_s3_path']
DATABASE = args['database_name']
TABLE_NAME = args['table_name']
PARTITION_KEY = args['partition_key']

KINESIS_STREAM_ARN = args['kinesis_stream_arn']
KINESIS_STREAM_NAME = get_kinesis_stream_name_from_arn(KINESIS_STREAM_ARN)

#XXX: starting_position_of_kinesis_iterator: ['LATEST', 'TRIM_HORIZON']
STARTING_POSITION_OF_KINESIS_ITERATOR = args.get('starting_position_of_kinesis_iterator', 'TRIM_HORIZON')

AWS_REGION = args['aws_region']
WINDOW_SIZE = args.get('window_size', '100 seconds')

conf_list = [
    (f"spark.sql.catalog.{CATALOG}", "org.apache.spark.sql.delta.catalog.DeltaCatalog"),
    ("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
]
conf = SparkConf().setAll(conf_list)
# Set the Spark + Glue context
sc = SparkContext(conf=conf)

# Set the Spark + Glue context
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

CREATE_DELTA_TABLE_SQL = f'''CREATE TABLE IF NOT EXISTS {DATABASE}.{TABLE_NAME} (
  product_id STRING,
  product_name STRING,
  price INT,
  category STRING,
  updated_at TIMESTAMP
) USING DELTA
PARTITIONED BY ({PARTITION_KEY})
LOCATION '{DELTA_S3_PATH}'
'''

spark.sql(CREATE_DELTA_TABLE_SQL)

# Read from Kinesis Data Stream
streaming_data = spark.readStream \
                    .format("kinesis") \
                    .option("streamName", KINESIS_STREAM_NAME) \
                    .option("endpointUrl", f"https://kinesis.{AWS_REGION}.amazonaws.com") \
                    .option("startingPosition", STARTING_POSITION_OF_KINESIS_ITERATOR) \
                    .load()

event_schema = StructType([
    StructField("product_id", StringType(), True),
    StructField("product_name", StringType(), True),
    StructField("price", IntegerType(), True),
    StructField("category", StringType(), True),
    StructField("updated_at", TimestampType(), True),
])

streaming_data_df = streaming_data \
    .select(from_json(col("data").cast("string"), \
                      event_schema)
            .alias("source_table")) \
    .select("source_table.*") \
    .withColumn('updated_at', to_timestamp(col('updated_at'), 'yyyy-MM-dd HH:mm:ss'))

checkpointPath = os.path.join(args["TempDir"], args["JOB_NAME"], "checkpoint/")

#query = streaming_data_df.writeStream \
#    .format("console") \
#    .trigger(processingTime=WINDOW_SIZE) \
#    .option("checkpointLocation", checkpointPath) \
#    .start()

query = streaming_data_df.writeStream \
    .format("delta") \
    .outputMode("append") \
    .trigger(processingTime=WINDOW_SIZE) \
    .option("path", DELTA_S3_PATH) \
    .option("checkpointLocation", checkpointPath) \
    .start()

query.awaitTermination()
