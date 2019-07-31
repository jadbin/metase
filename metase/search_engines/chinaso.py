# coding=utf-8

import logging
from urllib.request import quote, urljoin
import asyncio
from http.cookies import SimpleCookie

from tornado.httpclient import HTTPRequest, HTTPError

from xpaw import Selector, HttpRequest, HttpHeaders

from metase.search_engine import SearchEngine

log = logging.getLogger(__name__)


class Chinaso(SearchEngine):
    name = 'Chinaso'
    fake_url = True
    source_importance = 2

    page_size = 10

    def __init__(self):
        self.cookies = SimpleCookie()
        asyncio.ensure_future(self.update_cookies())

    def search_url(self, query):
        return 'http://www.chinaso.com/search/pagesearch.htm?q={}'.format(quote(query))

    def page_requests(self, query, **kwargs):
        max_records = kwargs.get('data_source_results')
        if max_records is None:
            max_records = self.page_size
        for page in range(0, max_records, self.page_size):
            url = 'http://www.chinaso.com/search/pagesearch.htm?q={}&page={}&wd={}'.format(quote(query),
                                                                                           page + 1,
                                                                                           quote(query))
            headers = HttpHeaders()
            headers.add('Cookie', self.convert_to_cookie_header(self.cookies))
            yield HttpRequest(url, headers=headers)

    def extract_results(self, response):
        # 更新Cookie
        self.cookies.update(self.get_cookies_in_response_headers(response.headers))

        selector = Selector(response.text)
        for item in selector.css('li.reItem'):
            a = item.css('h2>a')
            if len(a) <= 0:
                continue
            title = a[0].text.strip()
            text = None
            div = item.css('div.reNewsWrapper')
            if len(div) > 0:
                text = div[0].text.strip().split('\n')[0]
            url = urljoin('http://www.chinaso.com/search/', item.css('h2>a')[0].attr('href').strip())
            if text is not None:
                yield {'title': title, 'text': text, 'url': url}

    async def update_cookies(self):
        while True:
            try:
                url = 'http://www.chinaso.com/search/pagesearch.htm?q={}'.format(quote('中国搜索'))
                headers = self.default_headers()
                try:
                    resp = await self.http_client.fetch(HTTPRequest(url, headers=headers, follow_redirects=False))
                except HTTPError as e:
                    resp = e.response
                cookies = self.get_cookies_in_response_headers(resp.headers)
                self.cookies.update(cookies)
            except Exception as e:
                log.warning('Failed to update cookies: %s', e)
            finally:
                await asyncio.sleep(5 * 60)
