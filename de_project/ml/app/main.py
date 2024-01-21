"""Main module for a very very simple ML serving API.

This api is used to serve the model trained in the ML pipeline.
It has two endpoints:
    - /loadmodel - used to trigger reloading the model from storage (by POST request with model's path)
    - /predict - used to make price predictions using the loaded model (by POST request with data point)
"""
import logging
import os

import joblib
import minio
from fastapi import FastAPI
from pydantic import BaseModel


class DataPointDTO(BaseModel):
    data: list

class PredictionDTO(BaseModel):
    price: float

class ModelPathDTO(BaseModel):
    path: str

class DummyResponseDTO(BaseModel):
    msg: str


app = FastAPI(title="ML serving API")

@app.on_event("startup")
def load_model():
    app.model = None

@app.get("/")
def root():
    return {"message": "API is up and running"}

@app.post("/loadmodel", response_model=DummyResponseDTO)
def loadmodel(model_path: ModelPathDTO):
    try:
        minio_client = minio.Minio(
            os.getenv("MODELSTORE_ENDPOINT"),
            access_key=os.getenv("AWS_ACCESS_KEY_ID"),
            secret_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            secure=False
        )
        model_local_fname = model_path.path.split("/")[-1]
        minio_client.fget_object(
            os.getenv("DELTA_MAIN_TABLE_NAME"),
            model_path.path,
            model_path.path.split("/")[-1],
        )
        app.model = joblib.load(model_local_fname)
        msg = "ok"
    except Exception as e:
        logging.log(e)
        msg = "error"
    return DummyResponseDTO(msg=msg)

@app.post("/predict", response_model=PredictionDTO)
def predict(data_point: DataPointDTO):
    if app.model is not None:
        preds = app.model.predict(data_point.data)
    else:
        preds = -2137.0
        logging.info("Model not loaded!")
    logging.info(data_point)
    return PredictionDTO(price=preds[0])
