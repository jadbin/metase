# coding=utf-8

import json
import pickle
import time
import random
import hashlib
import logging

from xpaw import HttpRequest

log = logging.getLogger(__name__)


class Slave:
    def __init__(self, address, server):
        self.address = address
        self.downloader = server.downloader
        self.config = server.config
        self.api_version = self.config.get('api_version')
        self.timeout = self.config.get('timeout')
        self.api_url = 'http://{}/api/v{}/fetch'.format(self.address, self.api_version)
        self.api_secret = self.config.get('api_secret')

    def __str__(self):
        return repr(self.address)

    async def fetch(self, request, name):
        return await self._fetch(request, name, 'page')

    async def fetch_url(self, request, name):
        return await self._fetch(request, name, 'url')

    async def _fetch(self, request, name, rtype):
        body = pickle.dumps(request)
        timeout = self.config.get('timeout')
        req_headers = {'Content-Type': 'application/octet-stream'}

        timestamp = str(int(time.time()))
        nonce = str(random.randint(0, 1e8))
        signature = self.sign(body, name, rtype, timestamp, nonce)

        url = '{}?name={}&rtype={}&timestamp={}&nonce={}&signature={}'.format(self.api_url, name, rtype, timestamp,
                                                                              nonce, signature)
        req = HttpRequest(url, method='POST', headers=req_headers, body=body, timeout=timeout)
        resp = await self.downloader.fetch(req)
        real_resp = json.loads(resp.body)
        return real_resp

    def sign(self, body, name, rtype, timestamp, nonce):
        s = (self.api_secret + name + rtype + timestamp + nonce).encode('utf-8')
        h = hashlib.sha256(body + s).hexdigest()
        return h
