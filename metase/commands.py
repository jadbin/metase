# coding=utf-8

import logging

from metase import __version__
from metase.utils import load_config, iter_settings
from metase.run import run_server

log = logging.getLogger(__name__)


class Command:
    def __init__(self):
        self.exitcode = 0

    @property
    def name(self):
        return ""

    @property
    def syntax(self):
        return ""

    @property
    def short_desc(self):
        return ""

    @property
    def long_desc(self):
        return self.short_desc

    def add_arguments(self, parser):
        pass

    def process_arguments(self, args):
        pass

    def run(self, args):
        raise NotImplementedError


class Option:
    def __init__(self, name=None, cli=None, metavar=None, default=None, action=None, type=None, nargs=None,
                 short_desc=None):
        self.name = name
        self.cli = cli
        self.metavar = metavar
        self.default = default
        self.action = action
        self.type = type
        self.nargs = nargs
        self.short_desc = short_desc

    def add_argument(self, parser):
        if self.cli is None:
            return
        args = tuple(self.cli)
        kwargs = {'dest': self.name, 'help': self.short_desc}
        if self.metavar is not None:
            kwargs['metavar'] = self.metavar
        if self.action is not None:
            kwargs['action'] = self.action
        if self.type is not None:
            kwargs['type'] = self.type
        if self.nargs is not None:
            kwargs['nargs'] = self.nargs
        parser.add_argument(*args, **kwargs)


class RunCommand(Command):
    def __init__(self):
        super().__init__()
        self.config = {}
        self.options = [
            Option(name='daemon', cli=['-d', '--daemon'], action='store_true', short_desc='run in daemon mode'),
            Option(name='log_level', cli=['-l', '--log-level'], metavar='LEVEL', short_desc='log level'),
            Option(name='log_file', cli=['--log-file'], metavar='FILE', short_desc='log file'),
            Option(name='pid_file', cli=['--pid-file'], metavar='FILE', short_desc='PID file')]

    @property
    def name(self):
        return "run"

    @property
    def short_desc(self):
        return "Run meta search service"

    def add_arguments(self, parser):
        parser.add_argument('-c', '--config', dest='config', metavar='FILE',
                            help='configuration file')
        for s in self.options:
            s.add_argument(parser)

    def process_arguments(self, args):
        if args.config is not None:
            c = load_config(args.config)
            for k, v in iter_settings(c):
                self.config[k] = v
        for s in self.options:
            v = getattr(args, s.name)
            if v is not None:
                self.config[s.name] = v

    def run(self, args):
        run_server(self.config)


class VersionCommand(Command):
    @property
    def name(self):
        return "version"

    @property
    def short_desc(self):
        return "Print the version"

    def run(self, args):
        print("metase version {}".format(__version__))
