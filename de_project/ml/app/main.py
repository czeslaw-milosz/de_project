import logging
import os

import joblib
import modelstore
from fastapi import FastAPI
from pydantic import BaseModel


class DataPointDTO(BaseModel):
    data: dict

class PredictionDTO(BaseModel):
    price: float

class ModelIdDTO(BaseModel):
    model_id: str

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
def loadmodel(model_id:ModelIdDTO):
    try:
        model_store = modelstore.ModelStore.from_minio(
            access_key=os.environ["AWS_ACCESS_KEY_ID"],
            secret_key=os.environ["AWS_SECRET_ACCESS_KEY"],
            bucket_name=os.environ["MODEL_STORE_AWS_BUCKET"],
            root_prefix=os.environ["DELTA_MAIN_TABLE"],
        )
        model_path = model_store.download(
            local_path=".",
            domain="price_prediction",
            model_id=model_id.model_id,
        )
        app.model = joblib.load(model_path)
        msg = "ok"
    except Exception as e:
        logging.log(e)
        msg = "error"
    return DummyResponseDTO(msg=msg)

@app.post("/predict", response_model=PredictionDTO)
def classify(data_info: DataPointDTO):
    logging.info(data_info)
    return PredictionDTO(price=2137.0)
