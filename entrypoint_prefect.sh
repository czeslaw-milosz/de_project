#!/bin/sh
echo $PREFECT_API_URL
prefect cloud login -k $PREFECT_API_TOKEN  -w $PREFECT_WORKSPACE
cd /de_project
# while :; do :; done & kill -STOP $! && wait $!
python pipelines/process_crawl_flow.py
# bash
