""" A very very simple FastAPI app to run the crawl data processing Prefect pipeline. 

This app basically waits and listens and then triggers the prefect pipeline;
it has only one endpoint:
    - / - used to trigger the pipeline (by simple GET request)
"""
from fastapi import FastAPI

from pipelines import process_crawl_flow


app = FastAPI()

@app.get("/")
def read_root():
    process_crawl_flow.process_crawl_flow()
