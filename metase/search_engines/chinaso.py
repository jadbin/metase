# coding=utf-8

import logging
from urllib.request import quote, urljoin
import asyncio
from http.cookies import SimpleCookie

from xpaw import Selector, HttpRequest
from xpaw.errors import HttpError

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
        for num in range(0, max_records, self.page_size):
            url = 'http://www.chinaso.com/search/pagesearch.htm?q={}&page={}&wd={}'.format(quote(query),
                                                                                           num // self.page_size + 1,
                                                                                           quote(query))
            yield HttpRequest(url)

    def before_request(self, request):
        self.set_cookie_header(request, self.cookies)

    def after_request(self, response):
        self.cookies.update(self.get_cookies_in_response(response))

    def extract_results(self, response):
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
                try:
                    req = HttpRequest(url, allow_redirects=False)
                    await self.extension.handle_request(req)
                    resp = await self.downloader.fetch(req)
                except HttpError as e:
                    resp = e.response
                cookies = self.get_cookies_in_response(resp)
                self.cookies.update(cookies)
            except Exception as e:
                log.warning('Failed to update cookies: %s', e)
            finally:
                await asyncio.sleep(5 * 60)
