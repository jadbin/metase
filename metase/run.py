# coding=utf-8

import os
import logging
import signal

from tornado.ioloop import IOLoop

from metase.utils import configure_logger, configure_tornado_logger, daemonize
from metase.config import DEFAULT_CONFIG
from metase.server import MseServer

log = logging.getLogger(__name__)


def run_server(config):
    _c = dict(DEFAULT_CONFIG)
    _c.update(config)
    config = _c

    logger = configure_logger('metase', config)
    configure_tornado_logger(logger.handlers)
    if config.get('daemon'):
        daemonize()

    pid_file = config.get('pid_file')
    _write_pid_file(pid_file)
    try:
        server = MseServer(config)
        server.on_start()
        IOLoop.current().start()
    finally:
        _remove_pid_file(pid_file)


def _write_pid_file(pid_file):
    if pid_file is not None:
        with open(pid_file, 'w') as f:
            f.write(str(os.getpid()))


def _remove_pid_file(pid_file):
    if pid_file is not None:
        try:
            os.remove(pid_file)
        except Exception as e:
            log.warning('Cannot remove PID file %s: %s', pid_file, e)
