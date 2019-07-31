# coding=utf-8

import logging
from urllib.request import quote, urljoin
import asyncio
from http.cookies import SimpleCookie

from tornado.httpclient import HTTPRequest

from metase.search_engine import SearchEngine

from xpaw import Selector, HttpRequest, HttpHeaders

log = logging.getLogger(__name__)


class Sogou(SearchEngine):
    name = 'Sogou'
    fake_url = True
    source_importance = 2

    page_size = 50

    def __init__(self):
        self.cookies = SimpleCookie()
        self.cookies['com_sohu_websearch_ITEM_PER_PAGE'] = str(self.page_size)
        asyncio.ensure_future(self.update_cookies())

    def search_url(self, query):
        return 'https://www.sogou.com/web?query={}'.format(quote(query))

    def page_requests(self, query, **kwargs):
        max_records = kwargs.get('data_source_results')
        if max_records is None:
            max_records = self.page_size
        for page in range(0, max_records, self.page_size):
            url = 'https://www.sogou.com/web?page={}&query={}'.format(page + 1, quote(query))
            headers = HttpHeaders()
            headers.add('Cookie', self.convert_to_cookie_header(self.cookies))
            yield HttpRequest(url, headers=headers)

    def extract_results(self, response):
        # 更新Cookie
        self.cookies.update(self.get_cookies_in_response_headers(response.headers))

        selector = Selector(response.text)
        for item in selector.css('div.rb'):
            title = item.css('h3>a')[0].text.strip()
            text = None
            div_ft = item.css('div.ft')
            if len(div_ft) > 0:
                text = div_ft[0].text.strip()
            url = urljoin('https://www.sogou.com/', item.css('h3>a')[0].attr('href').strip())
            if text is not None:
                yield {'title': title, 'text': text, 'url': url}

    async def update_cookies(self):
        """
        避免被BAN，定时通过主页刷新Cookie
        """
        while True:
            try:
                resp = await self.http_client.fetch(HTTPRequest('https://www.sogou.com/'))
                self.cookies.update(self.get_cookies_in_response_headers(resp.headers))
            except Exception as e:
                log.warning('Failed to update cookies: %s', e)
            finally:
                await asyncio.sleep(5 * 60)
