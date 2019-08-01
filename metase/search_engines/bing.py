# coding=utf-8

import logging
from urllib.request import quote

from metase.search_engine import SearchEngine

from xpaw import Selector, HttpRequest

log = logging.getLogger(__name__)


class Bing(SearchEngine):
    name = 'Bing'
    fake_url = False
    source_importance = 3

    page_size = 10

    def search_url(self, query):
        return 'https://www.bing.com/search?q={}'.format(quote(query))

    def page_requests(self, query, **kwargs):


        max_records = kwargs.get('data_source_results')
        recent_days = kwargs.get('recent_days')
        site = kwargs.get('site')

        if site:
            site = site.replace('*.','') if site.startswith("*.") else site
            query = quote(query) + "+" + quote("site:") + quote(site)
        else:
            query = quote(query)

        if recent_days:
            if recent_days == 1:
                filters = 'ex1%3a"ez1"'
            elif recent_days == 7:
                filters = 'ex1%3a"ez2"'
            elif recent_days == 30:
                filters = 'ex1%3a"ez3"'
            else:
                raise ValueError('recent_days: {}'.format(recent_days))
            raw_url = 'https://www.bing.com/search?q={}&filters={}'.format(query, filters)
        else:
            raw_url = 'https://www.bing.com/search?q={}'.format(query)

        if max_records is None:
            max_records = self.page_size
        for num in range(0, max_records, self.page_size):
            url = '{}&first={}'.format(raw_url, num + 1)
            log.info("Bing: {}".format(url))
            yield HttpRequest(url)

    def extract_results(self, response):
        selector = Selector(response.text)
        for item in selector.css('li.b_algo'):
            title = item.css('h2>a')[0].text.strip()
            text = None
            span = item.css('div.b_caption>p')
            if len(span) > 0:
                text = span[0].text.strip()
            url = item.css('h2>a')[0].attr('href').strip()
            if text is not None:
                yield {'title': title, 'text': text, 'url': url}
