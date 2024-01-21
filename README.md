# de_project
Main repository for Data Engineering @ MIMUW 2024 course project

On a general level, the system is described in the video. Here deployment/running details are specified.

Prerequisites:
 - a working installation of `docker` and `docker-compose`
 - for running datahub, one should datahub installed for Python as described here: https://datahubproject.io/docs/quickstart/

First, please specify the configuration in `.env` and run `source .env`; everything can stay as-is *except* for Prefect Cloud API token, URL and workspace -- I'm using PRefect Cloud because I can't fit Prefect server alongside all the other containers on my laptop, also it seems to be the more production-suitable option.

To setup containers, go into project's main directory and run
```
docker compose up
```
Warning: on first run, this *will* take some time and data! (custom docker images are built and packages installed).

After everything gets set up, you should see Minio console on `localhost:9090`, Scrapyd crawl monitoring on `localhost:6800`, a container waiting to run PRefect pipeline on `localhost:8300` and a ML model serving API on `localhost:8200` (without a model yet).

To run crawlers:
```
make startspiders
```
(this sends a request to Scrapyd; you will be able to see the status on 6800).

To run Prefect pipeline (this assumes you already have scraped data in bronze layer on Minio):
```
make startflow
```
(this sends request that triggers pipeline; the run will be visible on Prefect Cloud).

In the end of the pipeline, a ML model will be trained and persisted to Minio; serving API will quickly reload and prediction will be possible on POST request at `localhost:8200/predict`.

Teardown by:
```
docker compose down && docker rm -f
```

Datahub was launched as follows:
```
cd dhub
python3 -m datahub docker quickstart --quickstart-compose-file ./docker-compose-without-neo4j-m1.quickstart.yml
```