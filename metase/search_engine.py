# coding=utf-8

import inspect
from http.cookies import SimpleCookie

from xpaw import HttpHeaders, HttpResponse

from metase.utils import walk_modules, get_default_headers


class SearchEngine:
    """
    搜索引擎，构造URL并从检索结果页面中提取数据

    name: 搜索引擎代号
    fake_url: 检索结果中的URL是否是虚假的
    source_importance: 搜索源的相对权重，1: 一般，2: 重要，3: 非常重要

    加载引擎前注入如下属性：
    http_client: HTTP客户端
    config: 配置
    """

    name = ''
    fake_url = False
    source_importance = 1

    http_client = None
    config = None

    def search_url(self, query):
        raise NotImplemented

    def page_requests(self, query, **kwargs):
        """
        构造检索请求
        :param query: 查询词
        :param kwargs: 配置参数
            data_source_results: 检索结果数量
            recent_days: 最近的检索结果，1: 最近一天，7: 最近一周，30: 最近一月
            site: 限定网站，例如: *.gov.cn
        :return: 检索请求的列表
        """
        raise NotImplemented

    def extract_results(self, response: HttpResponse):
        """
        提取检索结果页中的数据
        :param response: 检索页response
        :return: 检索结果的dict
            title: 标题
            text: 摘要
            url: 网页URL
        """
        raise NotImplemented

    def get_cookies_in_response_headers(self, headers: HttpHeaders):
        cookies = SimpleCookie()
        for s in headers.get_list('Set-Cookie'):
            cookies.load(s)
        return cookies

    def convert_to_cookie_header(self, cookies: SimpleCookie):
        return '; '.join('{}={}'.format(k, v.value) for k, v in cookies.items())

    @property
    def default_headers(self):
        if not hasattr(self, '_default_headers'):
            self._default_headers = get_default_headers()
        return self._default_headers


def load_search_engines():
    engines = {}
    for module in walk_modules('metase.search_engines'):
        for obj in vars(module).values():
            if inspect.isclass(obj) and issubclass(obj, SearchEngine) and obj.__module__ == module.__name__:
                engines[obj.name] = obj()
    return engines
