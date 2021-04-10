# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy
from scrapy import Field
from itemloaders.processors import Join, MapCompose, TakeFirst
from datetime import datetime


def ymd(date: datetime):
    return date.strftime("%Y-%m-%d")


class MatchreportsItem(scrapy.Item):
    link = Field(output_processor=TakeFirst())
    headline = Field(output_processor=TakeFirst())
    home_team = Field(output_processor=TakeFirst())
    away_team = Field(output_processor=TakeFirst())
    match_date = Field(input_processor=MapCompose(ymd), output_processor=TakeFirst())
    pictures = Field(output_processor=TakeFirst())
    author = Field(output_processor=TakeFirst())
    stadium = Field(output_processor=TakeFirst())
    text = Field()
    scrape_date = Field(input_processor=MapCompose(ymd), output_processor=TakeFirst())