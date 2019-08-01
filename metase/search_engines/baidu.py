# coding=utf-8

import logging
from urllib.request import quote

from metase.search_engine import SearchEngine

from xpaw import Selector, HttpRequest

import time
from datetime import datetime, timedelta

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
        recent_days = kwargs.get('recent_days')
        site = kwargs.get('site')
        if max_records is None:
            max_records = self.page_size

        if site:
            query = query + " site:" + site

        if recent_days:
            today = datetime.now()
            if recent_days == 1:
                start = today + timedelta(days=-1)
            elif recent_days == 7:
                start = today + timedelta(days=-7)
            elif recent_days == 30:
                start = today + timedelta(days=-30)
            else:
                raise ValueError('recent_days: {}'.format(recent_days))
            start, end = int(time.mktime(start.timetuple())), int(time.mktime(today.timetuple()))
            raw_url = 'http://www.baidu.com/s?wd={}&gpc=stf%3D{}%2C{}|stftype%3D1'.format(quote(query), start, end)
        else:
            raw_url = 'http://www.baidu.com/s?wd={}'.format(quote(query))

        for num in range(0, max_records, self.page_size):
            url = '{}&pn={}&rn={}'.format(raw_url, num, self.page_size)
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
