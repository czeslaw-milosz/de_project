#!/bin/sh
echo $PREFECT_API_URL
prefect cloud login -k $PREFECT_API_TOKEN  -w $PREFECT_WORKSPACE
cd /de_project/pipelines
echo "Ready to trigger flow (listening at port 8300)"
uvicorn app.main:app --host 0.0.0.0 --port 8300
