import datetime

import prefect
import pyspark
from prefect.runtime import flow_run, task_run
from pyspark.conf import SparkConf
from pyspark.context import SparkContext
from pyspark.streaming import StreamingContext
from pyspark.sql import SparkSession
from pyspark.sql import functions as f

import config
from pipelines import utils


@prefect.task(refresh_cache=True)
def preprocess_crawl(spark: pyspark.sql.SparkSession, lake_name: str, table_name: str) -> str:
    """Preprocess raw crawl data to the format used by the silver layer of the data lake.

    1. Standardize dataframe of raw crawl data.
    2. Deduplicate dataframe of scraped data.
    3. Apply shared preprocessing.
    4. Apply site-specific preprocessing.
    5. Write to silver table of Delta Lake.

    Args:
        table_url (str): URL of the Delta Lake table with raw crawl data.

    Returns:
        str: URL of the Delta Lake table with preprocessed crawl data.
    """
    df = spark.read.load(f"s3a://{lake_name}/{table_name}")
    df = utils.deduplicate(utils.standardize_raw_data(df))
    df = utils.preprocess_crawl_shared(df)
    df = utils.preprocess_crawl_site_specific(df)
    df = utils.ensure_schema(df, config.SILVER_TABLE_SCHEMA)
    output_table_url = f"s3a://{lake_name}/silver/crawl_data"
    df.write.format("delta").mode("append").save(output_table_url)
    return output_table_url


@prefect.task(refresh_cache=True)
def create_business_analytics_table(spark: pyspark.sql.SparkSession, lake_name: str, silver_table_url: str) -> str:
    """Create business analytics table from the silver table."""
    df = spark.read.load(
        silver_table_url
    ).select(
        "offer_date", "city", "price_total", "price_per_msq", "size",
    ).dropna(
        subset=["price_total", "price_per_msq"]
    ).orderBy("offer_date")
    output_table_url = f"s3a://{lake_name}/gold/price_analytics"
    df.write.format("delta").mode("overwrite").save(output_table_url)
    return output_table_url


@prefect.task(refresh_cache=True)
def create_ml_dataset(spark: pyspark.sql.SparkSession, lake_name: str, silver_table_url: str) -> str:
    """Create ML dataset from the silver table."""
    df = spark.read.load(
        silver_table_url
    ).select(
        *config.ML_FEATURES_SUBSET
    ).dropna(
        subset="price_total"
    )
    output_table_url = f"s3a://{lake_name}/gold/ml_dataset"
    df.write.format("delta").mode("overwrite").save(output_table_url)
    return output_table_url
