import logging
import os
import re
from datetime import datetime
from pathlib import Path

from twisted.internet import reactor
import scrapy

from settings import guardiansitesettings, settings

# TODO check error
# TODO use items, item loaders and default values to fix  errors.
# use  item_loader.add_value to  use  existing methods and probabaly create try except stuff
# or alternatively add the img attrib  stuff with add_css  and some filters from scrapy
# TODO  set some values to decrease banning prob. see bottom
# TODO out to s3
# TODO never repopulate (using a latest matchdate variable and a populated links in the data storage path)
# https://stackoverflow.com/questions/29396942/avoiding-scraping-data-from-pages-already-scraped
# TODO possibly make a statscollector to  check skipped pages or  so and use it to stop crawling


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

        next_page = response.css(".pagination__action--static::attr(href)").get()
        if next_page is not None:
            yield response.follow(next_page, self.parse)

    def parse_matchreport(self, response):
        date = re.search("\d{4}\/[a-z]{3}\/\d{2}", response.url).group()
        date = datetime.strptime(date, "%Y/%b/%d").strftime("%Y-%m-%d")
        teams = response.css(".css-184iqxr .css-w5gu9i::text").getall()
        self.log(f"Following link to page {response.url}")
        yield {
            "link": response.url,
            "headline": response.css(".css-dxy9hs::text").get(),
            "home_team": teams[0],
            "away_team": teams[1],
            "match_date": date,
            "pictures": [
                {"link": img.attrib["src"], "text": img.attrib["alt"]} for img in response.css("img") if "alt" in img.attrib.keys()
            ],
            "author": response.css(".css-lkdvty a::text").get(),
            "stadium": response.css(".css-lkdvty::text").re("(?=[A-Z]).*")[0],
            "text": response.css(".css-19t0h2c::text").getall(),
        }

    def stop(self):
        self.crawler.engine.close_spider(self, "timeout")


if __name__ == "__main__":
    from scrapy.crawler import CrawlerProcess

    process = CrawlerProcess(
        settings={
            "FEEDS": {
                f"s3://{settings.BUCKET_NAME}/scraping/feeds/%(name)s.jl": {"format": "json"},
            },
        }
    )

    process.crawl(GuardianSpider)
    process.start()

#   File "/Users/hojland/guardian_soccer_spider/src/spider.py", line 50, in <listcomp>
#    {"link": img.attrib["src"], "text": img.attrib["alt"]} for img in response.css("img") if "alt" in img.attrib.keys()
# KeyError: 'src'

# 2021-04-05 22:05:54 [scrapy.core.scraper] ERROR: Spider error processing <GET https://www.theguardian.com/football/2021/mar/07/manchester-city-manchester-united-premier-league-match-report> (referer: https://www.theguardian.com/football/premierleague+tone/matchreports?page=2)
#  2021-04-05 22:05:54 [scrapy.core.scraper] ERROR: Spider error processing <GET https://www.theguardian.com/football/2021/mar/06/burnley-arsenal-premier-league-report> (referer: https://www.theguardian.com/football/premierleague+tone/matchreports?page=2)

# rotate your user agent from a pool of well-known ones from browsers (google around to get a list of them)
# disable cookies (see COOKIES_ENABLED) as some sites may use cookies to spot bot behaviour
# use download delays (2 or higher). See DOWNLOAD_DELAY setting.
# if possible, use Google cache to fetch pages, instead of hitting the sites directly
# use a pool of rotating IPs. For example, the free Tor project or paid services like ProxyMesh. An open source alternative is scrapoxy, a super proxy that you can attach your own proxies to.
# use a highly distributed downloader that circumvents bans internally, so you can just focus on parsing clean pages. One example of such downloaders is Crawlera