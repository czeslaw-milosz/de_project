.PHONY : clean startflow

startspiders: # send requests to scrapyd server to start crawlers
	curl http://localhost:6800/schedule.json -d project=crawl -d spider=olx;
	curl http://localhost:6800/schedule.json -d project=crawl -d spider=otodom

startflow: # send request to trigger prefect data processing flow
	curl http://localhost:8300/

clean: # recursively clean python cache files
	find . -type d -name '__pycache__' -exec rm -rf {} +
	find . -type f -name '*.py[co]' -delete
