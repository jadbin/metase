# coding=utf-8

import logging
from urllib.request import quote

from metase.search_engine import SearchEngine

from xpaw import Selector, HttpRequest

log = logging.getLogger(__name__)


class Baidu(SearchEngine):
    name = 'Baidu'
    fake_url = True
    source_importance = 2

    page_size = 50

    def search_url(self, query):
        return 'https://www.baidu.com/s?wd={}'.format(quote(query))

    def page_requests(self, query, **kwargs):
        max_records = kwargs.get('data_source_results')
        if max_records is None:
            max_records = self.page_size
        for page in range(0, max_records, self.page_size):
            url = 'http://www.baidu.com/s?pn={}&wd={}&rn={}'.format(page, quote(query), self.page_size)
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
