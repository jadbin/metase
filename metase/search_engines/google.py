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
        max_records = kwargs.get('data_source_results')
        if max_records is None:
            max_records = self.page_size
        for num in range(0, max_records, self.page_size):
            url = 'https://www.google.com.hk/search?q={}&start={}'.format(quote(query), num)
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
