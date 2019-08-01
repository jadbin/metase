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
        """
        btf=d; btf=w; btf=m
        https://hk.search.yahoo.com/search?p=%E5%8C%97%E4%BA%AC+site%3A*.gov.cn
        """
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
                btf = 'd'
            elif recent_days == 7:
                btf = 'w'
            elif recent_days == 30:
                btf = 'm'
            else:
                raise ValueError('recent_days: {}'.format(recent_days))
            raw_url = 'https://hk.search.yahoo.com/search?q={}&btf={}'.format(query, btf)
        else:
            raw_url = 'https://hk.search.yahoo.com/search?q={}'.format(query)

        if max_records is None:
            max_records = self.page_size
        for num in range(0, max_records, self.page_size):
            url = '{}&first={}'.format(raw_url, num + 1)
            log.info("Yahoo: {}".format(url))
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
