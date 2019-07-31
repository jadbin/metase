# coding=utf-8

import pickle
import time
import random
import hashlib
import logging

from tornado.httpclient import HTTPRequest

log = logging.getLogger(__name__)


class Slave:
    def __init__(self, address, server):
        self.address = address
        self.http_client = server.http_client
        self.config = server.config
        self.api_version = self.config.get('api_version')
        self.timeout = self.config.get('timeout')
        self.fetch_url = 'http://{}/api/v{}/fetch'.format(self.address, self.api_version)
        self.api_secret = self.config.get('api_secret')

    def __str__(self):
        return repr(self.address)

    async def fetch(self, request):
        body = pickle.dumps(request)
        timeout = self.config.get('timeout')
        req_headers = {'Content-Type': 'application/octet-stream'}

        timestamp = str(int(time.time()))
        nonce = str(random.randint(0, 1e8))
        signature = self.sign(body, timestamp, nonce)

        url = '{}?timestamp={}&nonce={}&signature={}'.format(self.fetch_url, timestamp, nonce, signature)
        req = HTTPRequest(url, method='POST', headers=req_headers, body=body,
                          connect_timeout=timeout, request_timeout=timeout)
        resp = await self.http_client.fetch(req)
        real_resp = pickle.loads(resp.body)
        return real_resp

    def sign(self, body, timestamp, nonce):
        s = (self.api_secret + timestamp + nonce).encode('utf-8')
        h = hashlib.sha256(body + s).hexdigest()
        return h
