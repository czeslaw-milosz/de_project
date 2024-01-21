import os

import joblib
import minio
import pandas as pd
import polars as pl
import prefect
import requests
import sklearn
import xgboost as xgb
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.model_selection import RandomizedSearchCV, StratifiedKFold
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
    X_train = df.select(~pl.selectors.by_name("price_total")).to_pandas().dropna(axis="columns", how="all")
    y_train = df.select("price_total").to_pandas()
    search_cv.fit(X_train, y_train)
    best_model = search_cv.best_estimator_

    minioClient = minio.Minio(
        os.getenv("MODELSTORE_ENDPOINT"),
        access_key=os.getenv("AWS_ACCESS_KEY_ID"),
        secret_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        secure=False
    )
    model_fname = "pricepredictor.joblib"
    joblib.dump(best_model, model_fname)
    with open(model_fname, "rb") as file_data:
        file_stat = os.stat(model_fname)
        target_fname = f"gold/{model_fname}"
        minioClient.put_object(
            os.getenv("DELTA_MAIN_TABLE_NAME"),
            target_fname, 
            file_data,
            file_stat.st_size
    )
    return target_fname


@prefect.task
def notify_model_serving_api(model_fname: str, model_serving_url: str = "http://mlapi:8200/loadmodel/") -> None:
    """Notify the model serving API that a new model is available."""
    response = requests.post(model_serving_url, json={"path": model_fname})
    return response.status_code


def get_price_prediction_pipeline(categorical_columns) -> tuple[Pipeline, sklearn.model_selection.RandomizedSearchCV]:
    """Return a pipeline for predicting house prices."""
    impute_mean = SimpleImputer(missing_values=pd.NA, strategy="mean")
    impute_mode = SimpleImputer(missing_values=pd.NA, strategy="most_frequent")
    impute_const = SimpleImputer(missing_values=pd.NA, strategy="constant", fill_value="MISSING")

    imputer = ColumnTransformer([
        ("impute_mean", impute_mean, ["size", "rent"]),
        ("impute_mode", impute_mode, ["offer_type", "building_type", "year_built", "floor",
                                    "primary_market", "has_lift", "has_tv", "has_internet",
                                    "has_phone_line", "is_furnished", "has_dishwasher", "has_fridge",
                                    "has_oven", "has_stove", "has_washing_machine", "has_garden",
                                    "has_balcony", "has_porch", "has_parking", "gated_community",
                                    "guarded_building", "has_cctv", "n_rooms"]),
        ("impute_const", impute_const, ["construction_status", "ownership_type", "heating_type",
                                        "windows_type", "building_material"]),
    ], remainder=impute_const, verbose_feature_names_out=False).set_output(transform="pandas")

    categorical_transformer = Pipeline(
        steps=[
            ("encoder", OrdinalEncoder(handle_unknown="error")),
        ]
    )
    preprocessor = ColumnTransformer(
        transformers=[
            ("encode", categorical_transformer, categorical_columns),
        ],
        remainder="passthrough", verbose_feature_names_out=False 
    )
    model = Pipeline(
        steps=[("imputer", imputer), ("preprocessor", preprocessor), ("regressor", xgb.XGBRegressor())]
    )
    param_grid = param_grid = {
        "regressor__eta": [0.01, 0.05, 0.1, 0.2],
        "regressor__max_depth": [2, 3, 5, 7, 10],
        "regressor__n_estimators": list(range(100, 1000, 100)),
    }
    search_cv = RandomizedSearchCV(
        model, 
        param_grid,
        cv=StratifiedKFold(n_splits=3, shuffle=True),
        scoring="neg_root_mean_squared_error",
        n_iter=10,
        n_jobs=-1,
        refit=True,
        verbose=2,
        random_state=2137
    )
    return model, search_cv
