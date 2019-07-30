# coding=utf-8

import logging
from collections import defaultdict
import pickle
import asyncio
import re
import random
from urllib.request import urljoin
import math
import time

from tornado.web import Application, RequestHandler
from tornado.httpclient import HTTPRequest
from tornado.curl_httpclient import CurlAsyncHTTPClient

from xpaw import Downloader, HttpRequest, HttpHeaders
from xpaw.errors import HttpError, ClientError

from metase.search_engine import load_search_engines, SearchEngine

log = logging.getLogger(__name__)


class MseServer:
    """
    元搜索服务，包括：

    (1) 响应元搜索请求
    接收到元搜索请求后，向配置的slave节点下发下载任务，收集并合并检索结果

    (2) 响应下发的下载任务
    接收下载任务，返回网页源代码
    """

    def __init__(self, config):
        self.config = config

    def on_start(self):
        app = Application([
            (r'/api/v1/search', SearchHandler, dict(config=self.config)),
            (r'/api/v1/task', TaskHanlder, dict(config=self.config))
        ])
        app.listen(self.config.get('port'), self.config.get('host'))


class SearchHandler(RequestHandler):
    def initialize(self, config):
        self.config = config
        self.http_client = CurlAsyncHTTPClient(max_clients=config.get('max_clients'), force_instance=True)
        self.search_engines = self._load_search_engines()
        slaves = config.get('slaves')
        if not slaves:
            slaves = [{
                'address': 'localhost:{}'.format(config['port']),
                'allow': '*'
            }]
        self.slave_map = self._make_slave_map(slaves)
        self.api_version = self.config.get('api_version', 1)

    def _load_search_engines(self):
        SearchEngine.http_client = self.http_client
        SearchEngine.config = self.config
        return load_search_engines()

    def _make_slave_map(self, slaves):
        slave_map = defaultdict(list)
        for s in slaves:
            if s['allow'] == '*':
                allows = [i for i in self.search_engines]
            else:
                allows = s['allow'].split(',')
            for a in allows:
                slave_map[a.strip()].append(s['address'])
        return slave_map

    async def get(self):
        start_time = time.time()
        query = self.get_argument('query')
        sources = self.get_argument('sources', default=None)
        if sources is None:
            sources = [i for i in self.search_engines]
        else:
            sources = sources.split(',')
            for i in sources:
                if i not in self.search_engines:
                    self.write_error(400)
                    return
        data_source_results = self.get_argument('data_source_results', '20')
        data_source_results = int(data_source_results)

        req = {}
        for s in sources:
            req[s] = [i for i in self.search_engines[s].page_requests(query, data_source_results=data_source_results)]
        resp = {}
        req_list = []
        for i in req:
            resp[i] = [None] * len(req[i])
            for j in range(len(req[i])):
                req_list.append(self._get_response(req[i][j], i, resp[i], j))
        await asyncio.gather(*req_list)
        res = {}
        for i in resp:
            res[i] = []
            for t in resp[i]:
                if t is not None:
                    for r in self.search_engines[i].extract_results(t):
                        res[i].append(r)
            if len(res[i]) > data_source_results:
                res[i] = res[i][:data_source_results]

        fake_url_req_list = []
        for i in res:
            if self.search_engines[i].fake_url:
                for r in res[i]:
                    fake_url_req_list.append(self._get_real_url(r, i))
        await asyncio.gather(*fake_url_req_list)

        duration = time.time() - start_time
        req_meta = {
            'data_source_results': data_source_results,
            'query': query,
            'sources': sources
        }
        resp_meta = {
            'duration': round(duration, 3)
        }
        packed_results = self._pack_results(query, res, request_meta=req_meta, response_meta=resp_meta)
        self.write(packed_results)

    async def _get_response(self, request, name, result, index):
        slave = self.slave_available(name)
        if slave is None:
            return
        try:
            url = self._slave_task_url(slave)
            body = pickle.dumps(request)
            timeout = self.config.get('timeout')
            req_headers = {'Content-Type': 'application/octet-stream'}
            req = HTTPRequest(url, method='POST', headers=req_headers, body=body,
                              connect_timeout=timeout, request_timeout=timeout)
            resp = await self.http_client.fetch(req)
            real_resp = pickle.loads(resp.body)
            result[index] = real_resp
        except Exception as e:
            log.warning('Failed request slave %s: %s', slave, e)

    def slave_available(self, name):
        """
        选择一个可用的工作节点
        """
        if name not in self.slave_map or len(self.slave_map[name]) <= 0:
            return
        return random.choice(self.slave_map[name])

    def _slave_task_url(self, slave):
        return 'http://{}/api/v{}/task'.format(slave, self.api_version)

    async def _get_real_url(self, result, name):
        slave = self.slave_available(name)
        if slave is None:
            return
        try:
            url = self._slave_task_url(slave)
            real_url_req = HttpRequest(result['url'], allow_redirects=False)
            body = pickle.dumps(real_url_req)
            timeout = self.config.get('timeout')
            req_headers = {'Content-Type': 'application/octet-stream'}
            req = HTTPRequest(url, method='POST', headers=req_headers, body=body,
                              connect_timeout=timeout, request_timeout=timeout)
            resp = await self.http_client.fetch(req)
            real_resp = pickle.loads(resp.body)
            location = self._get_location(real_resp)
            if location is not None:
                result['url'] = urljoin(result['url'], location)
        except Exception as e:
            log.warning('Failed to get real location %s: %s', result['url'], e)

    location_reg = re.compile(r'location\.(?:replace\(|href=)[\'"](.+?)[\'"]')

    def _get_location(self, resp):
        if int(resp.status / 100) == 3:
            return resp.headers['Location']
        res = self.location_reg.search(resp.text)
        if res:
            return res.group(1)

    def _pack_results(self, query, results, request_meta=None, response_meta=None):
        """
        对检索结果打包成接口的返回格式
        :param query: 查询词
        :param results: 多引擎检索结果
        :param request_meta: request元信息
        :param response_meta: response元信息
        """
        if request_meta is None:
            request_meta = {}
        if response_meta is None:
            response_meta = {}

        merged_results = self._merge_search_results(results)
        request_meta['max_records'] = len(merged_results)
        response_meta['merged_records'] = len(merged_results)
        response_meta['sources'] = {}
        for s in results:
            records = 0
            for r in merged_results:
                if s in r['sources']:
                    records += 1
            response_meta['sources'][s] = {
                'records': records,
                'url': self.search_engines[s].search_url(query),
                'ban': False  # FIXME
            }

        res = {
            'meta': {
                'request': request_meta,
                'response': response_meta
            },
            'records': merged_results
        }
        return res

    def _merge_search_results(self, results):
        """
        根据URL合并多个搜索引擎的检索结果，保留相关性评分最高的标题和内容
        """
        self._compute_relevance(results)
        mm = {}
        for s in results:
            for r in results[s]:
                url = r['url']
                relevance = r['relevance']
                if url in mm:
                    o = mm[url]
                    if s not in o['record']['sources']:
                        o['record']['relevance'] += relevance
                        o['record']['sources'].append(s)
                        if relevance > o['relevance']:
                            o['relevance'] = relevance
                            o['record']['title'] = r['title']
                            o['record']['text'] = r['text']
                else:
                    r['sources'] = [s]
                    mm[url] = {'record': r, 'relevance': relevance}
        res = [o['record'] for o in mm.values()]
        if len(res) > 0:
            res.sort(key=lambda x: x['relevance'], reverse=True)
            max_relevance = res[0]['relevance']
            for i in range(len(res)):
                res[i]['id'] = i + 1
                relevance = math.ceil(res[i]['relevance'] * 10 / max_relevance)
                if relevance > 10:
                    relevance = 10
                res[i]['relevance'] = relevance
        return res

    def _compute_relevance(self, results):
        """
        根据搜索引擎添加检索结果的相关性评分
        """
        for s in results:
            imp = self.search_engines[s].source_importance
            records = results[s]
            for i in range(len(records)):
                loc_score = (math.sqrt(i + 1) + 2) / (math.sqrt(i + 1))
                records[i]['relevance'] = imp * loc_score


class TaskHanlder(RequestHandler):
    def initialize(self, config):
        self.config = config
        self.downloader = Downloader(max_clients=config.get('max_clients'))

    async def post(self):
        req = pickle.loads(self.request.body)
        req.timeout = self.config.get('timeout')
        if req.headers is None:
            req.headers = HttpHeaders()
        default_headers = self.config.get('default_headers')
        for k, v in default_headers.items():
            req.headers.setdefault(k, v)
        user_agent = self.config.get('user_agent')
        req.headers.setdefault('User-Agent', user_agent)
        try:
            resp = await self.downloader.fetch(req)
        except HttpError as e:
            resp = e.response
        except ClientError:
            self.write_error(503)
            return
        self.set_header('Content-Type', 'application/octet-stream')
        self.write(pickle.dumps(resp))
