# Define your item pipelines here
#
# Don"t forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html
import uuid
from dataclasses import asdict

import polars as pl
from scrapy.exporters import PythonItemExporter
from scrapy.pipelines.images import ImagesPipeline


class BatchDeltaExportPipeline:
    """Custom pipeline for exporting items to delta table in batches."""
    def __init__(self, batch_size, delta_endpoint, delta_table, delta_id, delta_key, site_name):
        self.batch_size = batch_size
        self.delta_endpoint = delta_endpoint
        self.delta_table = delta_table
        self.delta_id = delta_id
        self.delta_key = delta_key
        self.batch_items = []
        self.exporter = PythonItemExporter()
        self.site_name = site_name

    @classmethod
    def from_crawler(cls, crawler):
        settings = crawler.settings
        batch_size = settings.getint("EXPORT_BATCH_SIZE")
        delta_endpoint = settings.get("AWS_ENDPOINT_URL")
        delta_table = settings.get("DELTA_TABLE")
        delta_id = settings.get("AWS_ACCESS_KEY_ID")
        delta_key = settings.get("AWS_SECRET_ACCESS_KEY")
        site_name = ""
        # crawl_id = str(uuid.uuid4())
        return cls(batch_size=batch_size, delta_endpoint=delta_endpoint, delta_table=delta_table, 
                   delta_id=delta_id, delta_key=delta_key, site_name=site_name)

    def open_spider(self, spider):
        """ on spider open, create pulsar client and producer and initialize scrapy exporter. """
        self.site_name = spider.name

    def close_spider(self, spider):
        """ on spider close, export remaining items and close pulsar producer. """
        if self.batch_items:
            self.export_batch()

    def process_item(self, item, spider):
        """ Process items in batches (export only when batch is full). """
        self.batch_items.append(asdict(item))
        if len(self.batch_items) >= self.batch_size:
            self.export_batch()
        return item

    def export_batch(self):
        if self.batch_items:
            df = pl.DataFrame(self.batch_items)
            df.write_delta(
                target=f"s3://{self.delta_table}/{self.site_name}",
                mode="append",
                overwrite_schema=True,
                storage_options={
                    "AWS_ENDPOINT_URL": self.delta_endpoint,
                    "AWS_ACCESS_KEY_ID": self.delta_id,
                    "AWS_SECRET_ACCESS_KEY": self.delta_key,
                    "AWS_REGION": "us-east-1",
                    "AWS_ALLOW_HTTP": "true",
                    "AWS_S3_ALLOW_UNSAFE_RENAME": "true",
                    },
            )
            self.batch_items = []


class RootImagesPipeline(ImagesPipeline):
    """gets rid of scrapy's hardcoded '/full/' path"""
    def file_path(self, request, response=None, info=None, *, item=None):
        """This is the method used to determine file path"""
        path = super().file_path(request, response, info)
        return path.replace("full/", "")
