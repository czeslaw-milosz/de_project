from pyspark.sql.types import StructType, StructField, StringType, DateType, FloatType, IntegerType, ArrayType, BooleanType, TimestampType

SILVER_TABLE_SCHEMA = StructType(
    [StructField("offer_source", StringType(), True), 
     StructField("offer_id", StringType(), True), 
     StructField("date_scraped", DateType(), True), 
     StructField("title", StringType(), True), 
     StructField("canonical_url", StringType(), True), 
     StructField("short_description", StringType(), True), 
     StructField("description", StringType(), True), 
     StructField("offer_type", StringType(), True), 
     StructField("offer_date", DateType(), True), 
     StructField("modified_date", DateType(), True), 
     StructField("location", StringType(), True), 
     StructField("city", StringType(), True), 
     StructField("district", StringType(), True), 
     StructField("region", StringType(), True), 
     StructField("price_total", FloatType(), True), 
     StructField("price_per_msq", FloatType(), True), 
     StructField("size", FloatType(), True), 
     StructField("n_rooms", IntegerType(), True), 
     StructField("construction_status", StringType(), True), 
     StructField("ownership_type", StringType(), True), 
     StructField("floor", IntegerType(), True), 
     StructField("rent", FloatType(), True), 
     StructField("heating_type", StringType(), True), 
     StructField("year_built", IntegerType(), True), 
     StructField("building_type", StringType(), True), 
     StructField("windows_type", StringType(), True), 
     StructField("building_material", StringType(), True), 
     StructField("image_urls", ArrayType(StringType(), True), True), 
     StructField("images", ArrayType(StructType(
         [StructField("url", StringType(), True), 
          StructField("path", StringType(), True), 
          StructField("checksum", StringType(), True), 
          StructField("status", StringType(), True)]), 
        True), True), 
    StructField("scraper_timestamp", TimestampType(), True), 
    StructField("primary_market", BooleanType(), False), 
    StructField("has_lift", BooleanType(), True), 
    StructField("has_tv", BooleanType(), True), 
    StructField("has_internet", BooleanType(), True), 
    StructField("has_phone_line", BooleanType(), True), 
    StructField("is_furnished", BooleanType(), True), 
    StructField("has_dishwasher", BooleanType(), True), 
    StructField("has_fridge", BooleanType(), True), 
    StructField("has_oven", BooleanType(), True), 
    StructField("has_stove", BooleanType(), True), 
    StructField("has_washing_machine", BooleanType(), True), 
    StructField("has_garden", BooleanType(), True), 
    StructField("has_balcony", BooleanType(), True), 
    StructField("has_porch", BooleanType(), True), 
    StructField("has_parking", BooleanType(), False), 
    StructField("gated_community", BooleanType(), True), 
    StructField("guarded_building", BooleanType(), True), 
    StructField("has_cctv", BooleanType(), True)])

ML_FEATURES_SUBSET = [
    "price_total", "city", "size", "offer_type", "n_rooms",
    "construction_status", "ownership_type", "floor", "rent",
    "heating_type", "year_built", "building_type",
    "windows_type", "building_material", "primary_market", 
    "has_lift", "has_tv", "has_internet", "has_phone_line", "is_furnished",
    "has_dishwasher", "has_fridge", "has_oven", "has_stove", 
    "has_washing_machine", "has_garden", "has_balcony", 
    "has_porch", "has_parking", "gated_community", 
    "guarded_building", "has_cctv",
]
