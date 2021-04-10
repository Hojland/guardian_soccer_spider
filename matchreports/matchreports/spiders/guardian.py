import logging
import os
import re
from datetime import datetime
from pathlib import Path

from twisted.internet import reactor
import scrapy
from scrapy.loader import ItemLoader

from matchreports.settings import guardiansitesettings, settings
from matchreports.items import MatchreportsItem


def extract_attrib(img_objs):
    return [{k: v for k, v in img_obj.attrib.items()} for img_obj in img_objs]


class GuardianSpider(scrapy.Spider):
    name = "guardian-match-reports"

    def __init__(self, *args, **kwargs):
        self.timeout = int(kwargs.pop("timeout", "60"))
        super(GuardianSpider, self).__init__(*args, **kwargs)

    def start_requests(self):
        reactor.callLater(self.timeout, self.stop)

        urls = [guardiansitesettings.BASE_URL]
        for url in urls:
            yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response):
        matchreport_page_links = response.css(".js-headline-text::attr(href)").getall()
        yield from response.follow_all(matchreport_page_links, self.parse_matchreport)

        next_page = response.css(".pagination__text+ .pagination__action--static::attr(href)").get()
        if next_page is not None:
            yield response.follow(next_page, self.parse)

    def parse_matchreport(self, response):
        date = re.search("\d{4}\/[a-z]{3}\/\d{2}", response.url).group()
        date = datetime.strptime(date, "%Y/%b/%d")
        teams = response.css(".css-184iqxr .css-w5gu9i::text").getall()
        self.log(f"Following link to page {response.url}")
        pictures = extract_attrib(response.css("img"))
        guardian_loader = ItemLoader(MatchreportsItem(), response)
        guardian_loader.add_value("scrape_date", datetime.now())
        guardian_loader.add_value("link", response.url)
        guardian_loader.add_value("headline", response.css(".css-dxy9hs::text").get())
        guardian_loader.add_value("home_team", teams[0])
        guardian_loader.add_value("away_team", teams[1])
        guardian_loader.add_value("match_date", date)
        guardian_loader.add_value("author", response.css(".css-lkdvty a::text").get())
        guardian_loader.add_value("stadium", response.css(".css-lkdvty::text").re("(?=[A-Z]).*")[0])
        guardian_loader.add_value("text", response.css(".css-19th2c::text").getall())
        guardian_loader.add_value("pictures", pictures)
        yield guardian_loader.load_item()

    def stop(self):
        self.crawler.engine.close_spider(self, "timeout")


if __name__ == "__main__":
    from scrapy.crawler import CrawlerProcess
    from scrapy.utils.project import get_project_settings

    settings = get_project_settings()
    settings["FEEDS"] = {f"s3://{settings.BUCKET_NAME}/scraping/feeds/%(name)s.jl": {"format": "jl"}}
    process = CrawlerProcess(settings=settings)
    process.crawl(GuardianSpider)
    process.start()