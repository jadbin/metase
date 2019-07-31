# coding=utf-8

DEFAULT_CONFIG = {
    'daemon': False,
    'log_level': 'info',
    'log_format': '%(asctime)s %(name)s [%(levelname)s] %(message)s',
    'log_dateformat': '[%Y-%m-%d %H:%M:%S %z]',
    'max_clients': 100,
    'timeout': 10,
    'host': '0.0.0.0',
    'port': 9281,
    'default_headers': {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'zh-CN,zh;q=0.8',
        'Cache-Control': 'max-age=0',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    },
    'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.142 Safari/537.36',
    'api_version': '1',
    'api_secret': ''
}
