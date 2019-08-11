# coding=utf-8

import inspect
from http.cookies import SimpleCookie

from xpaw import HttpHeaders, HttpResponse, HttpRequest

from metase.utils import walk_modules


class SearchEngine:
    """
    搜索引擎，构造URL并从检索结果页面中提取数据

    name: 搜索引擎代号
    fake_url: 检索结果中的URL是否是虚假的
    source_importance: 搜索源的相对权重，1: 一般，2: 重要，3: 非常重要

    加载引擎前注入如下属性：
    downloader: HTTP客户端
    extension: 拓展
    config: 配置
    """

    name = ''
    fake_url = False
    source_importance = 1

    downloader = None
    extension = None
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

    def before_request(self, request: HttpRequest):
        """
        请求前的处理函数
        """

    def after_request(self, response: HttpResponse):
        """
        请求后的处理函数
        """

    def get_cookies_in_response(self, response: HttpResponse):
        cookies = SimpleCookie()
        for s in response.headers.get_list('Set-Cookie'):
            cookies.load(s)
        return cookies

    def set_cookie_header(self, request: HttpRequest, cookies: SimpleCookie):
        if request.headers is None:
            request.headers = HttpHeaders()
        h = '; '.join('{}={}'.format(k, v.value) for k, v in cookies.items())
        request.headers.add('Cookie', h)


def load_search_engines():
    engines = {}
    for module in walk_modules('metase.search_engines'):
        for obj in vars(module).values():
            if inspect.isclass(obj) and issubclass(obj, SearchEngine) and obj.__module__ == module.__name__:
                engines[obj.name] = obj()
    return engines
