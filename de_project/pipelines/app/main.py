from fastapi import FastAPI

from pipelines import process_crawl_flow


app = FastAPI()

@app.get("/")
def read_root():
    process_crawl_flow.process_crawl_flow()
