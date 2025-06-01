#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import sys
import argparse
import json
import random
import time
import datetime

import boto3
from mimesis.locales import Locale
from mimesis.schema import Field, Schema
from mimesis.providers.base import BaseProvider
from mimesis import Field, Fieldset, Schema

from datetime import datetime

class CustomDatetimeProvider(BaseProvider):
  class Meta:
    """Class for metadata."""
    name = "custom_datetime"

  def __init__(self, seed=47) -> None:
    super().__init__(seed=seed)
    self.random = random.Random(seed)

def main():
  parser = argparse.ArgumentParser()

  parser.add_argument('--region-name', action='store', default='us-east-1',
    help='aws region name (default: us-east-1)')
  parser.add_argument('--stream-name', help='The name of the stream to put the data record into')
  parser.add_argument('--max-count', default=10, type=int, help='The max number of records to put (default: 10)')
  parser.add_argument('--dry-run', action='store_true')
  parser.add_argument('--console', action='store_true', help='Print out records ingested into the stream')

  options = parser.parse_args()

  #field = Field(locale=Locale.EN, providers=[CustomDatetimeProvider])
  field = Field(Locale.EN, seed=0xff)

    # Define a custom function to format the timestamp
  def custom_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


  manufacturers = [
    "Mazda",
    "Lancia",
    "Peugeot",
    "Maybach",
    "Chevrolet",
    "Mercedes-Benz",
    "Nissan",
    "Volkswagen",
    "Fiat",
    "Daihatsu"
  ]

  _schema = lambda: {
    "product_id": field("uuid"),
    "product_name": field("car"),
    "price": field("integer_number", start=1000, end=12345),
    "category": field("choice", items=manufacturers),
    "updated_at": custom_timestamp(),
  }

  if not options.dry_run:
    kinesis_streams_client = boto3.client('kinesis', region_name=options.region_name)

  cnt = 0
  # Specify the number of iterations during Schema instantiation
  schema = Schema(schema=_schema, iterations=options.max_count)

  # Generate the records
  events = schema.create()
  print(events)

  for record in events:
    cnt += 1

    if options.dry_run:
      print(f"{json.dumps(record)}")
    else:
      res = kinesis_streams_client.put_record(
        StreamName=options.stream_name,
        Data=f"{json.dumps(record)}\n", # convert JSON to JSON Line
        PartitionKey=f"{record['product_id']}"
      )

      if options.console:
        print(f"{json.dumps(record)}")

      if cnt % 100 == 0:
        print(f'[INFO] {cnt} records are processed', file=sys.stderr)

      if res['ResponseMetadata']['HTTPStatusCode'] != 200:
        print(res, file=sys.stderr)
    time.sleep(random.choices([0.01, 0.03, 0.05, 0.07, 0.1])[-1])
  print(f'[INFO] Total {cnt} records are processed', file=sys.stderr)


if __name__ == '__main__':
  main()
