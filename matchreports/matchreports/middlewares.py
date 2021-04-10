import logging
import os
import time
import re
from datetime import datetime

from scrapy.http import Request
from scrapy.item import Item
from scrapy.utils.request import request_fingerprint
from scrapy.utils.project import data_path
from scrapy.utils.python import to_bytes
from scrapy.exceptions import NotConfigured
from scrapy import signals
import sqlite3

logger = logging.getLogger(__name__)

# Define here the models for your spider middleware
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/spider-middleware.html

from scrapy import signals

# useful for handling different item types with a single interface
from itemadapter import is_item, ItemAdapter


class MatchreportsSpiderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the spider middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_spider_input(self, response, spider):
        # Called for each response that goes through the spider
        # middleware and into the spider.

        # Should return None or raise an exception.
        return None

    def process_spider_output(self, response, result, spider):
        # Called with the results returned from the Spider, after
        # it has processed the response.

        # Must return an iterable of Request, or item objects.
        for i in result:
            yield i

    def process_spider_exception(self, response, exception, spider):
        # Called when a spider or process_spider_input() method
        # (from other spider middleware) raises an exception.

        # Should return either None or an iterable of Request or item objects.
        pass

    def process_start_requests(self, start_requests, spider):
        # Called with the start requests of the spider, and works
        # similarly to the process_spider_output() method, except
        # that it doesn’t have a response associated.

        # Must return only requests (not items).
        for r in start_requests:
            yield r

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)


class MatchreportsDownloaderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the downloader middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request, spider):
        # Called for each request that goes through the downloader
        # middleware.

        # Must either:
        # - return None: continue processing this request
        # - or return a Response object
        # - or return a Request object
        # - or raise IgnoreRequest: process_exception() methods of
        #   installed downloader middleware will be called
        return None

    def process_response(self, request, response, spider):
        # Called with the response returned from the downloader.

        # Must either;
        # - return a Response object
        # - return a Request object
        # - or raise IgnoreRequest
        return response

    def process_exception(self, request, exception, spider):
        # Called when a download handler or a process_request()
        # (from other downloader middleware) raises an exception.

        # Must either:
        # - return None: continue processing this exception
        # - return a Response object: stops process_exception() chain
        # - return a Request object: stops process_exception() chain
        pass

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)


class DeltaFetch(object):
    """
    This is a spider middleware to ignore requests to pages containing items
    seen in previous crawls of the same spider, thus producing a "delta crawl"
    containing only new items.
    This also speeds up the crawl, by reducing the number of requests that need
    to be crawled, and processed (typically, item requests are the most cpu
    intensive).
    """

    def __init__(self, dir, reset=False, stats=None):
        self.db = None
        self.dir = dir
        self.reset = reset
        self.stats = stats

    @classmethod
    def from_crawler(cls, crawler):
        s = crawler.settings
        if not s.getbool("DELTAFETCH_ENABLED"):
            raise NotConfigured
        dir = data_path(s.get("DELTAFETCH_DIR", "deltafetch"))
        reset = s.getbool("DELTAFETCH_RESET")
        o = cls(dir, reset, crawler.stats)
        crawler.signals.connect(o.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(o.spider_closed, signal=signals.spider_closed)
        return o

    def spider_opened(self, spider):
        if not os.path.exists(self.dir):
            os.makedirs(self.dir)
        dbpath = os.path.join(self.dir, f"{spider.name}.db")
        reset = self.reset or getattr(spider, "deltafetch_reset", False)
        try:
            self.db = kvstore(dbpath, reset=reset)
        except Exception:
            logger.warning(f"Failed to open DeltaFetch database at {dbpath}, trying to recreate it")
            if os.path.exists(dbpath):
                os.remove(dbpath)
            self.db = kvstore(dbpath, reset=reset)

    def spider_closed(self, spider):
        self.db.close()

    def process_spider_output(self, response, result, spider):
        for r in result:
            if isinstance(r, Request):
                key = self._get_key(r)
                val = self._get_val(r)
                if key in self.db.keys():
                    logger.info(f"Ignoring already visited: {r.url}")
                    if self.stats:
                        self.stats.inc_value("deltafetch/skipped", spider=spider)
                    continue
            elif isinstance(r, (Item, dict)):
                key = self._get_key(response.request)
                val = self._get_val(response.request)
                self.db[key] = val
                if self.stats:
                    self.stats.inc_value("deltafetch/stored", spider=spider)
            yield r

    def _get_key(self, request):
        key = request.meta.get("deltafetch_key") or request_fingerprint(request)
        # request_fingerprint() returns `hashlib.sha1().hexdigest()`, is a string
        return to_bytes(key)

    def _get_val(self, request):
        # if re.search("\d{4}\/[a-z]{3}\/\d{2}", request.url):
        #    date = re.search("\d{4}\/[a-z]{3}\/\d{2}", request.url).group()
        #    date = datetime.strptime(date, "%Y/%b/%d").strftime("%Y-%m-%d")
        # else:
        #    date = time.time()
        return time.time()


class kvstore(dict):
    def __init__(self, filename=None, reset=False):
        self.conn = sqlite3.connect(filename)
        if reset:
            del_table()
        self.conn.execute("CREATE TABLE IF NOT EXISTS kv (key text unique, value timestamp)")

    def close(self):
        self.conn.commit()
        self.conn.close()

    def del_table(self):
        self.conn.execute("DROP TABLE [IF EXISTS] kv")

    def __len__(self):
        rows = self.conn.execute("SELECT COUNT(*) FROM kv").fetchone()[0]
        return rows if rows is not None else 0

    def iterkeys(self):
        c = self.conn.cursor()
        for row in self.conn.execute("SELECT key FROM kv"):
            yield row[0]

    def itervalues(self):
        c = self.conn.cursor()
        for row in c.execute("SELECT value FROM kv"):
            yield row[0]

    def iteritems(self):
        c = self.conn.cursor()
        for row in c.execute("SELECT key, value FROM kv"):
            yield row[0], row[1]

    def keys(self):
        return list(self.iterkeys())

    def values(self):
        return list(self.itervalues())

    def items(self):
        return list(self.iteritems())

    def less_days_max_value(self, val, days: int = 14):
        return self.conn.execute(f"SELECT date({val}, '-{days} day') < MAX(value) FROM kv").fetchone()[0]

    def __contains__(self, key):
        return self.conn.execute("SELECT 1 FROM kv WHERE key = ?", (key,)).fetchone() is not None

    def __getitem__(self, key):
        item = self.conn.execute("SELECT value FROM kv WHERE key = ?", (key,)).fetchone()
        if item is None:
            raise KeyError(key)
        return item[0]

    def __setitem__(self, key, value):
        self.conn.execute("REPLACE INTO kv (key, value) VALUES (?,?)", (key, value))
        self.conn.commit()

    def __delitem__(self, key):
        if key not in self:
            raise KeyError(key)
        self.conn.execute("DELETE FROM kv WHERE key = ?", (key,))
        self.conn.commit()

    def __iter__(self):
        return self.iterkeys()