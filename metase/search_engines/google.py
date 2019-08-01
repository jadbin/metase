# coding=utf-8

import logging
from urllib.request import quote

from metase.search_engine import SearchEngine

from xpaw import Selector, HttpRequest

log = logging.getLogger(__name__)


class Google(SearchEngine):
    name = 'Google'
    fake_url = False
    source_importance = 3

    page_size = 10

    def search_url(self, query):
        return 'https://www.google.com.hk/search?q={}'.format(quote(query))

    def page_requests(self, query, **kwargs):
        """
        Day: tbs=qdr:d
        Week: tbs=qdr:w
        Year: tbs=qdr:y
        +site%3A*.gov.cn
        """
        max_records = kwargs.get('data_source_results')
        recent_days = kwargs.get('recent_days')
        site = kwargs.get('site')

        if site:
            query = quote(query) + "+" + quote("site:") + quote(site)
        else:
            query = quote(query)

        if recent_days:
            if recent_days == 1:
                tbs = 'qdr:d'
            elif recent_days == 7:
                tbs = 'qdr:w'
            elif recent_days == 30:
                tbs = 'qdr:m'
            else:
                raise ValueError('recent_days: {}'.format(recent_days))
            raw_url = 'https://www.google.com.hk/search?q={}&tbs={}'.format(query, tbs)
        else:
            raw_url = 'https://www.google.com.hk/search?q={}'.format(query)

        if max_records is None:
            max_records = self.page_size
        for num in range(0, max_records, self.page_size):
            url = '{}&start={}'.format(raw_url, num + 1)
            yield HttpRequest(url)

    def extract_results(self, response):
        selector = Selector(response.text)
        for item in selector.css('div.g'):
            title = item.css('h3')[0].text.strip()
            text = None
            span_st = item.css('span.st')
            if len(span_st) > 0:
                text = span_st[0].text.strip()
            url = item.css('div.r>a')[0].attr('href').strip()
            if text is not None:
                yield {'title': title, 'text': text, 'url': url}
