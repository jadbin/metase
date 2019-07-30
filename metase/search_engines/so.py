# coding=utf-8

import logging
from urllib.request import quote

from metase.search_engine import SearchEngine

from xpaw import Selector, HttpRequest

log = logging.getLogger(__name__)


class So(SearchEngine):
    name = 'So'
    fake_url = False
    source_importance = 1

    page_size = 10

    def search_url(self, query):
        return 'https://www.so.com/s?q={}'.format(quote(query))

    def page_requests(self, query, **kwargs):
        max_records = kwargs.get('data_source_results')
        if max_records is None:
            max_records = self.page_size
        for page in range(0, max_records, self.page_size):
            url = 'https://www.so.com/s?pn={}&q={}'.format(page + 1, quote(query))
            yield HttpRequest(url)

    def extract_results(self, response):
        selector = Selector(response.text)
        for item in selector.css('li.res-list'):
            title = item.css('h3>a')[0].text.strip()
            text = None
            res_desc = item.css('p.res-desc')
            if len(res_desc) > 0:
                text = res_desc[0].text.strip()
            h3_a = item.css('h3>a')[0]
            url = h3_a.attr('data-url')
            if not url:
                url = h3_a.attr('href').strip()
            if text is not None:
                yield {'title': title, 'text': text, 'url': url}
