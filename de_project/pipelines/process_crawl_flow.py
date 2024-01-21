import os

import prefect
from pyspark.conf import SparkConf
from pyspark.context import SparkContext
from pyspark.sql import SparkSession

from pipelines import ml_pipeline, transformations


@prefect.flow(name="process_crawl_flow", log_prints=True)
def process_crawl_flow():
    """ Run the whole crawl data processing Prefect pipeline.
    
    This pipeline is triggered by the FastAPI app in de_project/pipelines/app/main.py.
    There are following steps:
        1. Preprocess crawl data from the raw crawl data table and write to the silver table.
        2. Create business analytics table from the silver table.
        3. Create ML dataset from the silver table.
        4. Retrain price prediction model and save the artifact to the gold table.
        5. Notify the ML serving API about the new model.
    """
    spark_conf = (
        SparkConf()
        .set("spark.jars.packages", 'org.apache.hadoop:hadoop-client:3.3.4,org.apache.hadoop:hadoop-aws:3.3.4,io.delta:delta-spark_2.12:3.0.0')
        .set("spark.driver.memory", "6g")

        .set("spark.hadoop.fs.s3a.endpoint", "minio:9000")
        .set("spark.hadoop.fs.s3a.access.key", "admin")
        .set("spark.hadoop.fs.s3a.secret.key", "adminadmin" )
        .set("spark.hadoop.fs.s3a.path.style.access", "true") 
        .set("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
        .set('spark.hadoop.fs.s3a.aws.credentials.provider', 'org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider')
        .set("spark.hadoop.fs.s3a.connection.ssl.enabled", "false")

        .set("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") 
        .set("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .set("spark.databricks.delta.schema.autoMerge.enabled", "true") # enable adding columns on merge)
    ).setAppName("HousingPipeline")
    sc = SparkContext.getOrCreate(spark_conf)
    spark = SparkSession(sc)

    silver_table_url = transformations.preprocess_crawl(
        spark, lake_name=os.getenv("DELTA_MAIN_TABLE_NAME"), table_name="bronze/crawl/olx"
    )
    _ = transformations.preprocess_crawl(
        spark, lake_name=os.getenv("DELTA_MAIN_TABLE_NAME"), table_name="bronze/crawl/otodom"
    )
    business_analytics_table_url = transformations.create_business_analytics_table(
        spark, lake_name=os.getenv("DELTA_MAIN_TABLE_NAME"), silver_table_url=silver_table_url
    )
    ml_table_url = transformations.create_ml_dataset(
        spark, lake_name=os.getenv("DELTA_MAIN_TABLE_NAME"), silver_table_url=silver_table_url
    )
    model_fname = ml_pipeline.retrain_price_predictor(
        ml_table_url
    )
    status = ml_pipeline.notify_model_serving_api(
        model_fname=model_fname
    )
    return {
        "silver": silver_table_url, 
        "analytics": business_analytics_table_url,
        "ml": ml_table_url,
        "model_id": model_fname,
        "model_status": status,
    }

if __name__ == "__main__":
    process_crawl_flow()
