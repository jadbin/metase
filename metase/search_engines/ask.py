# coding=utf-8

# coding=utf-8

import logging
from urllib.request import quote

from metase.search_engine import SearchEngine

from xpaw import Selector, HttpRequest

log = logging.getLogger(__name__)


class Ask(SearchEngine):
    name = 'Ask'
    fake_url = False
    source_importance = 2

    page_size = 10

    def search_url(self, query):
        return 'https://www.search.ask.com/web?q={}'.format(quote(query))

    def page_requests(self, query, **kwargs):
        max_records = kwargs.get('data_source_results')
        if max_records is None:
            max_records = self.page_size
        for num in range(0, max_records, self.page_size):
            url = 'https://www.search.ask.com/web?q={}&page={}'.format(quote(query), num // self.page_size + 1)
            yield HttpRequest(url)

    def extract_results(self, response):
        selector = Selector(response.text)
        for item in selector.css('li.algo-result'):
            title = item.css('a.algo-title')[0].text.strip()
            text = None
            span = item.css('span.algo-summary')
            if len(span) > 0:
                text = span[0].text.strip()
            url = item.css('a.algo-title')[0].attr('href').strip()
            if text is not None:
                yield {'title': title, 'text': text, 'url': url}
