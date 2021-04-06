import scrapy
from scrapy import Field


class GuardianItem(scrapy.Item):
    link = Field()
    headline = Field()
    home_team = Field()
    away_team = Field()
    match_date = Field()
    pictures = Field()
    author = Field()
    stadium = Field()
    text = Field()
    scrape_date = Field(serializer=str)