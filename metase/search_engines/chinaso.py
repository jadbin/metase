# coding=utf-8

import logging
from urllib.request import quote, urljoin

from metase.search_engine import SearchEngine

from xpaw import Selector, HttpRequest

log = logging.getLogger(__name__)


class Chinaso(SearchEngine):
    name = 'Chinaso'
    fake_url = True
    source_importance = 2

    page_size = 10

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
            yield HttpRequest(url)

    def extract_results(self, response):
        selector = Selector(response.text)
        for item in selector.css('li.reItem'):
            title = item.css('h2>a')[0].text.strip()
            text = None
            div = item.css('div.reNewsWrapper')
            if len(div) > 0:
                text = div[0].text.strip().split('\n')[0]
            url = urljoin('http://www.chinaso.com/search/', item.css('h2>a')[0].attr('href').strip())
            if text is not None:
                yield {'title': title, 'text': text, 'url': url}
