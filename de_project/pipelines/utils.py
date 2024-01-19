import pyspark
import pyspark.sql.functions as f


def ensure_schema(df: pyspark.sql.DataFrame, master_schema: pyspark.sql.types.StructType) -> pyspark.sql.DataFrame:
    """Ensure that the dataframe has the given schema, filling in any missing columns with None values.

    Args:
        df (pyspark.sql.DataFrame): Input dataframe.
        master_schema (pyspark.sql.types.StructType): Schema to ensure.

    Returns:
        pyspark.sql.DataFrame: Dataframe with ensured schema.
    """
    return df.withColumns({
        field.name: f.lit(None).cast(field.dataType)
        for field in master_schema.fields
        if field.name not in df.columns
    }).withColumns({
        field.name: f.col(field.name).cast(field.dataType)
        for field in master_schema.fields
        if field.name in df.columns
    }).select(master_schema.fieldNames())


def standardize_raw_data(df: pyspark.sql.DataFrame) -> pyspark.sql.DataFrame:
    """Standardize dataframe of raw crawl data.

    1. Replace missing value strings with None.
    2. Drop any null rows (they happen very rarely due to scraper errors).
    3. Drop mis-scraped rows with missing values in the `offer_id` or `price_total` column (such data is unusable by any other pipeline).
    4. Replace artifact newline and \r characters in the `short_description` and `description` columns with spaces.

    Args:
        df (pyspark.sql.DataFrame): Input dataframe.

    Returns:
        pyspark.sql.DataFrame: Standardized dataframe.
    """
    return df.replace(
        {"": None, "BRAK INFORMACJI": None, "MISSING": None, "brak informacji": None, "missing": None, "None": None}
        ).dropna(
            how="all",
        ).dropna(
            how="any", subset=["offer_id", "price_total"]
        ).withColumns({
            "short_description": f.regexp_replace(f.col("short_description"), r'[\n\r]', " "),
            "description": f.regexp_replace(f.col("description"), r'[\n\r]', " "),
        })


def deduplicate(df: pyspark.sql.DataFrame) -> pyspark.sql.DataFrame:
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


def preprocess_crawl_shared(df: pyspark.sql.DataFrame) -> pyspark.sql.DataFrame:
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
        "n_rooms": f.col("n_rooms").cast("int"),
        "price_total": f.round(f.regexp_replace(f.regexp_replace(f.col("price_total"), r" zł", ""), r" ", "").cast("float"), 2),
        "price_per_msq": f.round(f.col("price_per_msq").cast("float"), 2),
        "size": f.round(f.col("size").cast("float"), 2),
        "offer_id": f.concat(f.col("offer_source"), f.lit("_"), f.col("offer_id")),
        "offer_date": f.to_date(f.col("offer_date"), "yyyy-mm-dd"),
        "modified_date": f.to_date(f.col("modified_date"), "yyyy-mm-dd"),
        "scraper_timestamp": f.to_timestamp(f.col("date_scraped")),
        "date_scraped": f.to_date(f.split("date_scraped", " ").getItem(0), "yyyy-mm-dd"),
        })


def preprocess_crawl_site_specific(df: pyspark.sql.DataFrame) -> pyspark.sql.DataFrame:
    """Apply site-specific processing to dataframe of crawl data.
    
    Input is assumed to be standardized as in `standardize_raw_data` AND preprocessed as in `preprocess_crawl_data`.
    Currently, the system supports two sites: otodom.pl and olx.pl.

    Returns:
        pyspark.sql.DataFrame: Processed dataframe.
    """
    assert not (
        df.where(f.col("offer_source").contains("olx")).count() > 0 
        and df.where(f.col("offer_source").contains("otodom")).count() > 0
    ), "Dataframe contains offers from both otodom.pl and olx.pl. This is not supported in the current pipeline!"
    current_site = df.select("offer_source").distinct().collect()[0][0]
    assert current_site in ["otodom", "olx"], f"Site {current_site} is not supported in the current pipeline!"
    return preprocess_otodom(df) if current_site == "otodom" else preprocess_olx(df)


def preprocess_otodom(df: pyspark.sql.DataFrame) -> pyspark.sql.DataFrame:
    """Apply site-specific processing to dataframe of crawl data from otodom.pl.
    
    Input is assumed to be standardized as in `standardize_raw_data` AND preprocessed as in `preprocess_crawl_data`.

    Returns:
        pyspark.sql.DataFrame: Processed dataframe.
    """
    return df.withColumns({
        "primary_market": f.when(f.col("market") != "wtórny", True).otherwise(False),
        "offer_type": f.when(f.col("offer_type").isNull(), None).when(f.col("offer_type") == "prywatny", "private_owner").otherwise("company"),
        "year_built": f.col("year_built").cast("int"),
        "has_lift": f.when(f.col("lift").isNotNull(), f.col("lift") == "tak").otherwise(None),
        "has_tv": f.col("media_types").contains("telewizja kablowa"),
        "has_internet": f.col("media_types").contains("internet"),
        "has_phone_line": f.col("media_types").contains("telefon"),
        "rent": f.round(f.regexp_replace(f.regexp_replace(f.col("rent"), r" zł", ""), r" ", "").cast("float"), 2),
        "is_furnished": f.col("equipment").contains("meble"),
        "has_dishwasher": f.col("equipment").contains("zmywarka"),
        "has_fridge": f.col("equipment").contains("lodówka"),
        "has_oven": f.col("equipment").contains("piekarnik"),
        "has_stove": f.col("equipment").contains("kuchenka"),
        "has_washing_machine": f.col("equipment").contains("pralka"),
        "has_garden": f.col("outdoor").contains("ogródek"),
        "has_balcony": f.col("outdoor").contains("balkon"),
        "has_porch": f.col("outdoor").contains("taras"),
        "has_parking": f.col("parking").isNotNull(),
        "gated_community": f.col("security").contains("teren zamknięty"),
        "guarded_building": f.col("security").contains("ochrona"),
        "has_cctv": f.col("security").contains("monitoring"),
        "city": f.lower(f.col("city")),
    }).replace(
    {"drewniane": "wood", "plastikowe": "pvc", "aluminiowe": "aluminium"}, subset="windows_type"
    ).replace(
    {"beton": "concrete", "cegła": "brick", "silikat": "silicate", 
        "żelbet": "reinforced_concrete", "wielka płyta": "prefabricated", 
        "pustak": "honeycomb", "inne": "other"}, subset="building_material"
    ).replace(
        {"elektryczne": "electricity", "gazowe": "gas", "miejskie": "municipal", 
        "kotłownia": "boiler_room", "inne": "other"}, subset="heating_type"
    ).replace(
        {"użytkowanie wieczyste / dzierżawa": "usufruct", "spółdzielcze wł. prawo do lokalu": "co_op",
        "pełna własność": "full_ownership", "udział": "share", "inne": "other"}, subset="ownership_type"
    ).replace(
        {"do remontu": "for_renovation", "do wykończenia": "unfinished",
        "do zamieszkania": "ready", "inne": "other"}, subset="construction_status"
    ).replace(
        {"blok": "block", "szeregowiec": "row_housing", "apartamentowiec": "apartment_building",
        "dom wolnostojący": "house", "kamienica": "tenement", "inne": "other"}, subset="building_type"
    ).drop(
        "media_types", "lift", "equipment", "market", "outdoor", "parking", "security"
    )


def preprocess_olx(df: pyspark.sql.DataFrame) -> pyspark.sql.DataFrame:
    """Apply site-specific processing to dataframe of crawl data from olx.pl.
    
    Input is assumed to be standardized as in `standardize_raw_data` AND preprocessed as in `preprocess_crawl_data`.

    Returns:
        pyspark.sql.DataFrame: Processed dataframe.
    """
    return df.withColumns({
        "offer_type": f.when(f.col("offer_type").isNull(), None).when(f.col("offer_type") == "Prywatne", "private_owner").otherwise("company"),
        "city": f.lower(f.col("city")),
    }).replace(
        {"Loft": "loft", "Blok": "block", "Szeregowiec": "row_housing", "Apartamentowiec": "apartment_building",
        "Dom wolnostojący": "house", "Kamienica": "tenement", "Pozostałe": "other"}, subset="building_type"
    )
