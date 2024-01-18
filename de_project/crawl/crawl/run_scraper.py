import logging

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings


logging.basicConfig(level=logging.INFO)

process = CrawlerProcess(get_project_settings())
logging.getLogger("scrapy.core.scraper").info(
    f"Starting crawler process with settings:\n{get_project_settings().attributes}")

process.crawl("olx")
process.start()