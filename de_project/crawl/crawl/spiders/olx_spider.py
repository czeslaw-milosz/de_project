import datetime
import locale
import logging

from itemloaders.processors import Identity, TakeFirst
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy.loader import ItemLoader

from crawl import olx_utils
from crawl.items import OlxItem

# Suppress scrapy's unreasonable default logging of the whole scraped content
logging.getLogger("scrapy.core.scraper").addFilter(
    lambda x: not x.getMessage().startswith("Scraped from"))
locale.setlocale(locale.LC_ALL,'pl_PL.utf-8')


class OlxSpider(CrawlSpider):
    name = "olx"
    custom_settings = {
        "LOG_FILE": f"logs/{name}.log",
    }
    allowed_domains = [
        "olx.pl",
        "m.olx.pl",
    ]
    start_urls = [
        "https://www.olx.pl/nieruchomosci/mieszkania/sprzedaz/warszawa/",
        "https://www.olx.pl/nieruchomosci/mieszkania/sprzedaz/krakow/",
        "https://www.olx.pl/nieruchomosci/mieszkania/sprzedaz/wroclaw/",
    ]
    rules = (
        # Extract links matching data-testid='pagination-forward' and follow links from them (no callback means follow=True by default).
        Rule(LinkExtractor(restrict_xpaths="//a[@data-testid='pagination-forward']")),
        # Extract links matching 'd/oferta' but not redirecting to otodom.pl, and parse them with the spider's method parse_details
        Rule(LinkExtractor(allow=(r"d/oferta",), deny="otodom"), callback="parse_details"),
    )

    def parse_details(self, response):
        l = ItemLoader(item=OlxItem(), response=response)
        l.default_output_processor = TakeFirst()
        l.image_urls_out = Identity()
        l.images_out = Identity()

        l.add_value("offer_source", "olx")
        offer_id = response.xpath("//div[@data-cy='ad-footer-bar-section']/span/text()").getall()[-1] or ""
        l.add_value("offer_id", offer_id)
        l.add_value("date_scraped", datetime.datetime.now())
        l.add_xpath("title", "//title/text()")
        l.add_xpath("canonical_url", "//link[@rel='canonical']/@href")
        l.add_xpath("short_description", "//meta[@name='description']/@content")
        l.add_xpath("description", "//div[@data-cy='ad_description']/div//text()")
        price_total, location_district, location_city, location_region = olx_utils.get_fields_from_script_elt(response)
        l.add_value("price_total", price_total)
        l.add_value("location", ";".join((location_district, location_city, location_region)))
        l.add_value("city", location_city)
        l.add_value("district", location_district)
        l.add_value("region", location_region)

        offer_type, price_per_msq, primary_market, floor, building_type, size, n_rooms = olx_utils.get_detail_fields(response)
        l.add_value("offer_type", offer_type)
        l.add_value("price_per_msq", price_per_msq)
        l.add_value("primary_market", primary_market)
        l.add_value("floor", floor)
        l.add_value("building_type", building_type)
        l.add_value("size", size)
        l.add_xpath("n_rooms", n_rooms)

        offer_date = response.xpath("//span[@data-cy='ad-posted-at']/text()").get().replace("o ", "")
        if "Dzisiaj" in offer_date:
            offer_date.replace("Dzisiaj", datetime.datetime.now().strftime("%Y-%m-%d"))
        else:
            offer_date = datetime.datetime.strptime(offer_date, "%d %B %Y").strftime("%Y-%m-%d")
        l.add_value("offer_date", offer_date)
        l.add_value("modified_date", offer_date)

        image_urls = response.xpath("//div[@class='swiper-zoom-container']/img/@src").getall()
        l.add_value("image_urls", image_urls)

        yield l.load_item()
