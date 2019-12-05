# coding=utf-8

import logging
from urllib.request import quote
from http.cookies import SimpleCookie
import asyncio

from metase.search_engine import SearchEngine

from xpaw import Selector, HttpRequest

import time
from datetime import datetime, timedelta

log = logging.getLogger(__name__)


class Baidu(SearchEngine):
    name = 'Baidu'
    fake_url = True
    source_importance = 2

    page_size = 10

    def __init__(self):
        self.cookies = SimpleCookie()
        asyncio.ensure_future(self.update_cookies())

    def search_url(self, query):
        return 'https://www.baidu.com/s?wd={}'.format(quote(query))

    def page_requests(self, query, **kwargs):
        max_records = kwargs.get('data_source_results')
        recent_days = kwargs.get('recent_days')
        site = kwargs.get('site')
        if max_records is None:
            max_records = self.page_size

        if site:
            query = query + " site:" + site

        if recent_days:
            today = datetime.now()
            if recent_days == 1:
                start = today + timedelta(days=-1)
            elif recent_days == 7:
                start = today + timedelta(days=-7)
            elif recent_days == 30:
                start = today + timedelta(days=-30)
            else:
                raise ValueError('recent_days: {}'.format(recent_days))
            start, end = int(time.mktime(start.timetuple())), int(time.mktime(today.timetuple()))
            raw_url = 'http://www.baidu.com/s?wd={}&gpc=stf%3D{}%2C{}|stftype%3D1'.format(quote(query), start, end)
        else:
            raw_url = 'http://www.baidu.com/s?wd={}'.format(quote(query))

        for num in range(0, max_records, self.page_size):
            url = '{}&pn={}'.format(raw_url, num)
            yield HttpRequest(url)

    def extract_results(self, response):
        selector = Selector(response.text)
        for item in selector.css('div.result'):
            title = item.css('h3>a')[0].text.strip()
            text = None
            abstract = item.css('div.c-abstract')
            if len(abstract) > 0:
                text = abstract[0].text.strip()
            url = item.css('h3>a')[0].attr('href').strip()
            if text is not None:
                yield {'title': title, 'text': text, 'url': url}

    def before_request(self, request):
        self.set_cookie_header(request, self.cookies)

    def after_request(self, response):
        self.cookies.update(self.get_cookies_in_response(response))

    async def update_cookies(self):
        """
        避免被BAN，定时通过主页刷新Cookie
        """
        while True:
            try:
                req = HttpRequest('http://www.baidu.com/')
                await self.extension.handle_request(req)
                resp = await self.downloader.fetch(req)
                self.cookies.update(self.get_cookies_in_response(resp))
            except Exception as e:
                log.warning('Failed to update cookies: %s', e)
            finally:
                await asyncio.sleep(5 * 60)
