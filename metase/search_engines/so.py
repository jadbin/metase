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
        recent_days = kwargs.get('recent_days')
        site = kwargs.get('site')

        if site:
            query = query + " site:" + site

        if recent_days:
            if recent_days == 1:
                adv_t = 'd'
            elif recent_days == 7:
                adv_t = 'w'
            elif recent_days == 30:
                adv_t = 'm'
            else:
                raise ValueError('recent_days: {}'.format(recent_days))
            raw_url = 'https://www.so.com/s?q={}&adv_t={}'.format(quote(query), adv_t)
        else:
            raw_url = 'https://www.so.com/s?q={}'.format(quote(query))

        if max_records is None:
            max_records = self.page_size
        for num in range(0, max_records, self.page_size):
            url = '{}&pn={}'.format(raw_url, num / self.page_size + 1)
            log.info("SO: {}".format(url))
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
