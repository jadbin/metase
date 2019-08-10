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
import hashlib

from tornado.web import Application, RequestHandler
from tornado.curl_httpclient import CurlAsyncHTTPClient

from xpaw import Downloader, HttpRequest, HttpHeaders
from xpaw.errors import HttpError, ClientError

from metase.search_engine import load_search_engines, SearchEngine
from metase.slave import Slave
from metase.utils import get_default_headers

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
        self.http_client = CurlAsyncHTTPClient(max_clients=config.get('max_clients'), force_instance=True)
        self.search_engines = self._load_search_engines()
        slaves = config.get('slaves')
        # 没有配置slave的情况下将自身设置为slave
        if not slaves:
            slaves = [{
                'address': 'localhost:{}'.format(config['port']),
                'allow': '*'
            }]
        self.slave_map = self._make_slave_map(slaves)
        self.api_version = self.config.get('api_version')
        self.downloader = Downloader(max_clients=config.get('max_clients'))

    def on_start(self):
        apis = [
            ('/api/v{}/fetch'.format(self.api_version), FetchHanlder, dict(server=self))
        ]
        if not self.config.get('only_slave'):
            apis.append(('/api/v{}/search'.format(self.api_version), SearchHandler, dict(server=self)))

        app = Application(apis)
        host = self.config.get('host')
        port = self.config.get('port')
        app.listen(port, host)
        log.info('meta search service is available on %s:%s', host, port)

    async def meta_search(self, query, **kwargs):
        sources = kwargs.get('sources')
        if sources is None:
            sources = [i for i in self.search_engines]
        else:
            sources = [i for i in sources.split(',') if i in self.search_engines]
        data_source_results = kwargs.get('data_source_results')
        if data_source_results is None:
            data_source_results = 20
        recent_days = kwargs.get('recent_days')
        site = kwargs.get('site')
        request_params = dict(data_source_results=data_source_results,
                              recent_days=recent_days,
                              site=site)

        start_time = time.time()
        req = {}
        for s in sources:
            req[s] = []
            se = self.search_engines[s]
            for r in se.page_requests(query, **request_params):
                log.info('%s: %s', se.name, r.url)
                req[s].append(r)
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
                    try:
                        for r in self.search_engines[i].extract_results(t):
                            res[i].append(r)
                    except Exception as e:
                        log.warning('Failed to extract results from %s: %s', self.search_engines[i].name, e)
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
        return packed_results

    def _load_search_engines(self):
        SearchEngine.http_client = self.http_client
        SearchEngine.config = self.config
        return load_search_engines()

    def _make_slave_map(self, slaves):
        slave_map = defaultdict(list)
        for s in slaves:
            slave = Slave(s['address'], self)
            if s['allow'] == '*':
                allows = [i for i in self.search_engines]
            else:
                allows = s['allow'].split(',')
            for a in allows:
                slave_map[a.strip()].append(slave)
        return slave_map

    async def _get_response(self, request, name, result, index):
        slave = self._slave_available(name)
        if slave is None:
            return
        try:
            resp = await slave.fetch(request)
            result[index] = resp
        except Exception as e:
            log.warning('Failed request %s on slave %s: %s', request.url, slave, e)

    def _slave_available(self, name):
        """
        选择一个可用的工作节点
        """
        if name not in self.slave_map or len(self.slave_map[name]) <= 0:
            return
        return random.choice(self.slave_map[name])

    async def _get_real_url(self, result, name):
        slave = self._slave_available(name)
        if slave is None:
            return
        try:
            real_url_req = HttpRequest(result['url'], allow_redirects=False)
            resp = await slave.fetch(real_url_req)
            location = self._get_location(resp)
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


class SearchHandler(RequestHandler):
    def initialize(self, server):
        self.server = server

    def set_default_headers(self):
        self.set_header('Access-Control-Allow-Origin', '*')
        self.set_header('Access-Control-Allow-Headers', 'X-Requested-With')
        self.set_header('Access-Control-Allow-Methods', 'POST, PUT, GET, DELETE, OPTIONS')

    async def get(self):
        query = self.get_argument('query')
        sources = self.get_argument('sources', default=None)
        data_source_results = self.get_argument('data_source_results', default=None)
        if data_source_results is not None:
            data_source_results = int(data_source_results)
        recent_days = self.get_argument('recent_days', default=None)
        if recent_days is not None:
            recent_days = int(recent_days)
        site = self.get_argument('site', default=None)
        packed_results = await self.server.meta_search(query,
                                                       sources=sources,
                                                       data_source_results=data_source_results,
                                                       recent_days=recent_days,
                                                       site=site)
        self.write(packed_results)
        self.finish()


class FetchHanlder(RequestHandler):
    def initialize(self, server):
        self.config = server.config
        self.downloader = server.downloader
        self.api_secret = self.config.get('api_secret')

    async def post(self):
        if not self.verify_request():
            self.send_error(403)
            return

        req = pickle.loads(self.request.body)
        req.timeout = self.config.get('timeout')
        if req.headers is None:
            req.headers = HttpHeaders()
        default_headers = get_default_headers()
        for k, v in default_headers.items():
            req.headers.setdefault(k, v)
        log.info('Request: %s', req.url)
        try:
            resp = await self.downloader.fetch(req)
        except HttpError as e:
            resp = e.response
            log.info('Http Error: %s, %s', resp.status, resp.url)
        except ClientError as e:
            log.warning('Failed to request %s: %s', req.url, e)
            self.send_error(503)
            return
        else:
            log.info('Response: %s', resp.url)
        self.set_header('Content-Type', 'application/octet-stream')
        self.write(pickle.dumps(resp))
        self.finish()

    def verify_request(self):
        t = int(time.time())
        timestamp = self.get_argument('timestamp')
        nonce = self.get_argument('nonce')
        signature = self.get_argument('signature')

        s = (self.api_secret + timestamp + nonce).encode('utf-8')
        h = hashlib.sha256(self.request.body + s).hexdigest()
        if h != signature:
            return False
        if abs(t - int(timestamp)) > 600:
            return False
        return True
