from typing import Any

import scrapy
import ujson


def get_detail_fields(response: scrapy.http.response.html.HtmlResponse) -> tuple[Any]:
    """Extract details fields from response of olx scraper.
    
    Args:
        response (scrapy.http.response.html.HtmlResponse): response of olx scraper

    Returns:
        tuple: tuple of details extracted from response:
            - offer_type (str): type of the offer (private or business, "Prywatne" or "Firmowe")
            - price_per_msq (float): price of the flat per m^2
            - primary_market (boolean): whether the flat is on primary market (True) or resold (False)
            - floor (str): on which floor the flat is located
            - building_type (str): type of the building
            - size (float): size of the flat in square meters
            - n_rooms (int): number of rooms in the flat
    """
    # select from body an unordered list with class css-sfcl1s and extract texts of paragraphs in its items, including spans within paragraphs:
    list_items = response.xpath("//ul[@class='css-sfcl1s']/li/p//text()").getall()
    tmp = [x for x in list_items if x in {"Prywatne", "Firmowe"}]
    offer_type = tmp[0] if tmp else ""

    tmp = [x for x in list_items if "zł/m" in x]
    price_per_msq = tmp[0].split(" ")[3].strip().replace(",", ".") if tmp else ""

    primary_market = any("Pierwotny" in item for item in list_items)

    tmp = [x for x in list_items if "Poziom" in x]
    floor = tmp[0].split(":")[1].strip() if tmp else ""

    tmp = [x for x in list_items if "Rodzaj zabudowy" in x]
    building_type = tmp[0].split(":")[1].strip() if tmp else ""

    tmp = [x for x in list_items if "Powierzchnia" in x]
    size = tmp[0].split(" ")[1].strip().replace(",", ".") if tmp else ""

    tmp = [x for x in list_items if "Liczba pokoi" in x]
    n_rooms = tmp[0].split(" ")[2].strip() if tmp else ""

    return offer_type, price_per_msq, primary_market, floor, building_type, size, n_rooms


def get_fields_from_script_elt(response) -> tuple[str, str, str, str]:
    script_elt = response.xpath("//script[@id='olx-init-config']/text()").get()
    js_dict = ujson.loads(ujson.loads(
        script_elt.split("\n")[4].strip().replace("window.__PRERENDERED_STATE__= ", "")[:-1]
    ))
    param_dicts = js_dict["ad"]["ad"]["params"]
    price_total = js_dict["ad"]["ad"]["price"]["displayValue"] or ""
    location_district = js_dict["ad"]["ad"]["location"]["districtName"] or ""
    location_city = js_dict["ad"]["ad"]["location"]["cityName"] or ""
    location_region = js_dict["ad"]["ad"]["location"]["regionNormalizedName"] or ""
    return price_total, location_district, location_city, location_region


