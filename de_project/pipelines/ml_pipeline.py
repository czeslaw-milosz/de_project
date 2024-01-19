import os

import modelstore
import pandas as pd
import polars as pl
import prefect
import sklearn
import xgboost as xgb
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.model_selection import RandomizedSearchCV
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder

from typing import Any


@prefect.task
def retrain_price_predictor(ml_gold_table_url: str) -> dict[Any]:
    df = pl.read_delta(
        source=ml_gold_table_url,
        storage_options={
            "AWS_ENDPOINT_URL": os.getenv("AWS_ENDPOINT_URL"),
            "AWS_ACCESS_KEY_ID": os.getenv("AWS_ACCESS_KEY_ID"),
            "AWS_SECRET_ACCESS_KEY": os.getenv("AWS_SECRET_ACCESS_KEY"),
            "AWS_REGION": "us-east-1",
            "AWS_ALLOW_HTTP": "true",
            # "AWS_S3_ALLOW_UNSAFE_RENAME": "true",
        }
    ).drop(["offer_date"])
    categorical_columns = df.select(~pl.selectors.by_dtype(pl.NUMERIC_DTYPES)).columns
    model, search_cv = get_price_prediction_pipeline(categorical_columns)
    X_train = df.select(~pl.selectors.by_name("price_total")).to_pandas().dropna(axis="columns")
    y_train = df.select("price_total").to_pandas()
    search_cv.fit(X_train, y_train)
    best_model = search_cv.best_estimator_


    model_store = create_minio_model_store()
    meta_data = model_store.upload("price-prediction", model=best_model)
    return meta_data


def get_price_prediction_pipeline(categorical_columns) -> tuple[Pipeline, sklearn.model_selection.RandomizedSearchCV]:
    """Return a pipeline for predicting house prices."""
    impute_mean = SimpleImputer(missing_values=pd.NA, strategy="mean")
    impute_mode = SimpleImputer(missing_values=pd.NA, strategy="most_frequent")
    impute_const = SimpleImputer(missing_values=pd.NA, strategy="constant", fill_value="MISSING")

    imputer = ColumnTransformer([
        ("impute_size", impute_mean, ["size"]),
        ("impute_offer_type", impute_mode, ["offer_type"]),
        ("impute_building_type", impute_mode, ["building_type"]),
        ("impute_consts", impute_const, ["construction_status", "ownership_type", "heating_type",
                                        "windows_type", "building_material", ]),
        ("impute_rent", impute_mean, ["rent"]),
        ("impute_year", impute_mode, ["year_built"]),
    ], remainder=impute_const)

    categorical_transformer = Pipeline(
        steps=[
            ("encoder", OrdinalEncoder(handle_unknown="error")),
        ]
    )
    preprocessor = ColumnTransformer(
        transformers=[
            ("encode", categorical_transformer, categorical_columns),
        ]
    )
    model = Pipeline(
        steps=[("imputer", imputer), ("preprocessor", preprocessor), ("regressor", xgb.XGBRegressor())]
    )
    param_grid = param_grid = {
        "regressor__eta": list(range(0.01, 0.2, 0.01)),
        "regressor__max_depth": [2, 3, 5, 7, 10],
        "regressor__n_estimators": list(range(100, 1000, 100)),
    }
    search_cv = RandomizedSearchCV(
        model, 
        param_grid,
        scoring="neg_root_mean_squared_error",
        n_iter=2,
        n_jobs=-1,
        refit=True,
        random_state=2137
    )
    
    return model, search_cv


def create_minio_model_store() -> modelstore.ModelStore:
    """A model store that uses an s3 bucket with a MinIO client"""
    return modelstore.ModelStore.from_minio(
        access_key=os.environ["AWS_ACCESS_KEY_ID"],
        secret_key=os.environ["AWS_SECRET_ACCESS_KEY"],
        bucket_name=os.environ["MODEL_STORE_AWS_BUCKET"],
        root_prefix=os.environ["DELTA_MAIN_TABLE"],
    )

