import datetime
from typing import Any

import deltalake
import prefect
import pyspark
from prefect.runtime import flow_run, task_run
from pyspark.conf import SparkConf
from pyspark.context import SparkContext
from pyspark.streaming import StreamingContext
from pyspark.sql import SparkSession
from pyspark.sql import functions as f
from pyspark.sql.types import StringType


@prefect.task
def standardize_raw_data(df: pyspark.sql.DataFrame):
    """Standardize dataframe of raw crawl data.

    1. Replace missing value strings with None.
    2. Drop mis-scraped rows with missing values in the `offer_id` or `price_total` column (such data is unusable by any other pipeline).
    3. Replace artifact newline and \r characters in the `short_description` and `description` columns with spaces.

    Args:
        df (pyspark.sql.DataFrame): Input dataframe.

    Returns:
        pyspark.sql.DataFrame: Standardized dataframe.
    """
    return df.replace(
        {"": None, "BRAK INFORMACJI": None, "MISSING": None}
        ).dropna(
            subset=["offer_id", "price_total"]
        ).withColumns({
            "short_description": f.regexp_replace(f.col("short_description"), r'[\n\r]', " "),
            "description": f.regexp_replace(f.col("description"), r'[\n\r]', " "),
        })


@prefect.task
def deduplicate(df: pyspark.sql.DataFrame):
    """Deduplicate dataframe of scraped data (input is assumed to be standardized as in `standardize_raw_data`).

    For now, only basic deduplication based on exact matching of `offer_id` or `short_description` is performed.
    In the future, more advanced deduplication methods based on images similarity should be implemented.

    Args:
        df (pyspark.sql.DataFrame): Input dataframe.

    Returns:
        pyspark.sql.DataFrame: Deduplicated dataframe.
    """
    return df.dropDuplicates(
        subset=["offer_id"]
        ).dropDuplicates(
            subset=["short_description"]
        )


@prefect.task
def clean_data(df: pyspark.sql.DataFrame):
    """Clean dataframe of scraped data (input is assumed to be standardized as in `standardize_raw_data`).

    1. Convert prices to floats.
    2. Convert floor numbers to integers (0 = ground floor, -1 = basement, 11 = above 10th floor).
    3.Convert m^2 sizes to floats.

    Args:
        df (pyspark.sql.DataFrame): Input dataframe.

    Returns:
        pyspark.sql.DataFrame: Standardized dataframe.
    """
    df = df.replace(
            {"Parter": "0", "Suterena": "-1", "Powyżej 10": "11"}, 
            subset=["floor"]
        )
    return df.withColumns({
        "floor": f.col("floor").cast("int"),
        "price_total": f.regexp_replace(f.regexp_replace(f.col("price_total"), r" zł", ""), r" ", "").cast("float"),
        "price_per_msq": f.col("price_per_msq").cast("float"),
        "size": f.col("size").cast("float"),
        })

