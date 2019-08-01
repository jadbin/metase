# coding=utf-8

import logging
from urllib.request import quote, unquote
import re

from metase.search_engine import SearchEngine

from xpaw import Selector, HttpRequest

log = logging.getLogger(__name__)


class Yahoo(SearchEngine):
    name = 'Yahoo'
    fake_url = False
    source_importance = 3

    page_size = 10

    def search_url(self, query):
        return 'https://hk.search.yahoo.com/search?p={}'.format(quote(query))

    def page_requests(self, query, **kwargs):
        max_records = kwargs.get('data_source_results')
        if max_records is None:
            max_records = self.page_size
        for num in range(0, max_records, self.page_size):
            url = 'https://hk.search.yahoo.com/search?p={}&b={}'.format(quote(query), num + 1)
            yield HttpRequest(url)

    yahoo_url_reg = re.compile(r'/RU=(.+?)/')

    def extract_results(self, response):
        selector = Selector(response.text)
        for item in selector.css('div.algo-sr'):
            title = item.css('h3>a')[0].text.strip()
            text = None
            p_lh_l = item.css('p.lh-l')
            if len(p_lh_l) > 0:
                text = p_lh_l[0].text.strip()
            url = item.css('h3>a')[0].attr('href').strip()
            url = unquote(self.yahoo_url_reg.search(url).group(1))
            if text is not None:
                yield {'title': title, 'text': text, 'url': url}
