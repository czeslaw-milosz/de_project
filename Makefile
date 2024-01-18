.PHONY : clean

clean: # recursively clean python cache files
	find . -type d -name '__pycache__' -exec rm -rf {} +
	find . -type f -name '*.py[co]' -delete

