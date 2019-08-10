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
        """
        tsn=1&sourceid=inttime_day
        tsn=2&sourceid=inttime_week
        tsn=3&sourceid=inttime_month
        北京+site%3A*.gov.cn
        """
        max_records = kwargs.get('data_source_results')
        recent_days = kwargs.get('recent_days')
        site = kwargs.get('site')

        if site:
            query = query + " site:" + site
        else:
            query = query

        if recent_days:
            if recent_days == 1:
                tsn, sourceid = 1, "inttime_day"
            elif recent_days == 7:
                tsn, sourceid = 2, "inttime_week"
            elif recent_days == 30:
                tsn, sourceid = 3, "inttime_month"
            else:
                raise ValueError('recent_days: {}'.format(recent_days))
            raw_url = 'https://www.sogou.com/web?query={}&tsn={}&sourceid={}'.format(quote(query), tsn, sourceid)
        else:
            raw_url = 'https://www.sogou.com/web?query={}'.format(quote(query))

        if max_records is None:
            max_records = self.page_size
        for num in range(0, max_records, self.page_size):
            url = '{}&page={}'.format(raw_url, num // self.page_size + 1)
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
