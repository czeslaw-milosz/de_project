import datetime
from typing import Any

import scrapy
import ujson


OTODOM_DETAILS_FIELD2HTML = {
    "size": "table-value-area",
    "n_rooms": "table-value-rooms_num",
    "construction_status": "table-value-construction_status",
    "ownership_type": "table-value-building_ownership",
    "floor": "table-value-floor",
    "rent": "table-value-rent",
    "outdoor": "table-value-outdoor",
    "parking": "table-value-car",
    "heating_type": "table-value-heating",
    "market": "table-value-market",
    "offer_type": "table-value-advertiser_type",
    "year_built": "table-value-build_year",
    "building_type": "table-value-building_type",
    "windows_type": "table-value-windows_type",
    "lift": "table-value-lift",
    "media_types": "table-value-media_types",
    "security": "table-value-security_types",
    "equipment": "table-value-equipment_types",
    "building_material": "table-value-building_material",
}


def get_detail_fields(response: scrapy.http.response.html.HtmlResponse) -> tuple[Any]:
    """Extract data from main details fields from response of otodom scraper.
    
    Args:
        response (scrapy.http.response.html.HtmlResponse): response of otodom scraper

    Returns:
        dict(str, Any): details extracted from response fields (if extraction was possible, this is NOT always the case):
            - size (float): size of the flat in square meters
            - n_rooms (int): number of rooms in the flat
            - construction_status (str): construction status of the building
            - ownership_type (str): ownership type of the building
            - floor (str): on which floor the flat is located
            - rent (float): rent of the flat in PLN
            - outdoor (str): type of outdoor space available
            - parking (str): type of parking available
            - heating_type (str): type of heating available
            - market (str): type of market (primary or resold)
            - offer_type (str): type of the offer (private or business)
            - year_built (str): year in which the building was built
            - building_type (str): type of the building
            - windows_type (str): type of windows in the building
            - lift (str): whether the building has a lift or not
            - media_types (str): types of media available
            - security (str): types of security available
            - equipment (str): types of equipment available
            - building_material (str): type of building material used
    """
    output = {}
    return {
        field_name: response.xpath(f"//div[@data-testid='{html_name}']/text()").get() or None
        for field_name, html_name in OTODOM_DETAILS_FIELD2HTML.items()
    }

def get_image_urls(response: scrapy.http.response.html.HtmlResponse, img_size: str = "medium") -> list[str]:
    """Extract image urls from response of otodom scraper.
    
    Args:
        response (scrapy.http.response.html.HtmlResponse): response of otodom scraper
        img_size (str, optional): size of the image to extract (as defined by the crawled website). Defaults to "medium".

    Returns:
        list(str): list of image urls
    """
    item_json = ujson.loads(
        response.xpath("//script[@id='__NEXT_DATA__']/text()").get()
    )
    return [
        img_url[img_size]
        for img_url in item_json["props"]["pageProps"]["ad"]["images"]
    ]


def get_fields_from_script_elt(response: scrapy.http.response.html.HtmlResponse) -> tuple[str, str, str, str]:
    """ Extract fields from an embedded script element of otodom scraper response.

    Args:
        response (scrapy.http.response.html.HtmlResponse): response of otodom scraper

    Returns:
        tuple: tuple of fields extracted from response (if extraction was possible, this is NOT always the case):
            - offer_id (str): unique id of the offer
            - district (str): district in which the flat is located
            - city (str): city in which the flat is located
            - region (str): region in which the flat is located
    """
    json_data = ujson.loads(
        response.xpath("//script[@id='__NEXT_DATA__']/text()").get()
    )
    original_offer_id = json_data["props"]["pageProps"]["ad"]["id"] or ""
    city = json_data["props"]["pageProps"]["ad"]["target"]["City"] or ""
    try:
        district = json_data["props"]["pageProps"]["ad"]["location"]["address"]["district"]["name"] or ""
    except:
        district = ""
    try:
        region = json_data["props"]["pageProps"]["ad"]["target"]["Province"] or ""
    except:
        region = ""
    return f"otodom_{original_offer_id}", city, district, region


def get_posting_dates(response: scrapy.http.response.html.HtmlResponse) -> tuple[str|None, str|None]:
    """Extract offer's posting and modification date from response of otodom scraper.

    Args:
        response (scrapy.http.response.html.HtmlResponse): response of otodom scraper

    Returns:
        tuple: tuple of dates extracted from response (if extraction was possible, this is NOT always the case):
            - offer_date (str): date on which the offer was posted
            - modified_date (str): date on which the offer was modified
    """
    page_attrs = ujson.loads(
        response.xpath("//script[@id='__NEXT_DATA__']/text()").get()
    )
    offer_date = page_attrs["props"]["pageProps"]["ad"]["createdAt"] or None
    if offer_date:
        offer_date = datetime.datetime.strptime(offer_date, "%Y-%m-%dT%H:%M:%f%z").strftime("%Y-%m-%d")
    modified_date = page_attrs["props"]["pageProps"]["ad"]["modifiedAt"] or None
    if modified_date:
        modified_date = datetime.datetime.strptime(modified_date, "%Y-%m-%dT%H:%M:%f%z").strftime("%Y-%m-%d")
    return offer_date, modified_date
