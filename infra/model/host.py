import concurrent
import itertools
import os

from munch import Munch

from automation_infra.utils.timer import timeitdecorator
from infra.model import plugins

EXAMPLE_IP = '35.231.0.137'

host_config_example1 = {
    "ip": EXAMPLE_IP,
    "user": "user",
    "password": "pass",
    "alias": "monster",
    "host_id": 123,
    "host_type": "virtual",
    "allocation_id": ""
}

host_config_example2 = {
    "ip": EXAMPLE_IP,
    "user": "root",
    "key_file_path": "runner/docker_build/docker_user.pem",
    "alias": "monster",
    "host_id": 123,
    "host_type": "virtual",
    "allocation_id": ""
}

host_config_example3 = {
    "ip": EXAMPLE_IP,
    "user": "root",
    "password": "pass",
}


class Host(object):

    def __init__(self, host_config):
        _pem = host_config.pop('key_file_path', None)
        _pass = host_config.pop('password', None)
        assert (_pass and not _pem) or (_pem and not _pass), \
            "password and key are mutually exclusive (password=%s, key=%s)" % (_pass, _pem)
        self.ip = host_config.pop('ip')
        self.user = host_config.pop('user')
        try:
            self.port = host_config.pop('port')
        except KeyError:
            self.port = 22
        try:
            self.tunnelport = host_config.pop('tunnelport')
        except KeyError:
            self.tunnelport = 2222
        self.password = _pass
        self.keyfile = _pem
        self.extra_config = host_config
        self.__plugins = {}
        self._temp_dir_counter = itertools.count()

    def __getattr__(self, name):
        if name not in self.__plugins:
            # Access by key but if there's a problem raise an AttributeError to be consistent with expected behavior
            try:
                self.__plugins[name] = plugins.plugins[name](self)
            except KeyError:
                print(f"plugin {name} wasnt found!")
                raise AttributeError
        return self.__plugins[name]

    def mktemp(self, basedir=None, prefix=None, suffix=None):
        counter = self.unique()
        suffix = suffix or ""
        basedir = basedir or '/tmp'
        prefix = prefix or "_tmp_"
        return '/%(basedir)s/%(prefix)s%(counter)d%(suffix)s' % dict(basedir=basedir, prefix=prefix, counter=counter,
                                                                     suffix=suffix)


    def remove_plugin(self, name):
        if name in self.__plugins:
            self.__plugins.pop(name)

    def clear_plugins(self):
        self.__plugins.clear()

    def unique(self):
        return next(self._temp_dir_counter)

    def __str__(self):
        return self.ip

    @classmethod
    def from_args(cls, ip, user, password=None, pem_path=None, port=22):
        return cls(Munch.fromDict({"ip": ip,
        "port": port,
        "user": user,
        "password": password,
        "key_file_path": pem_path}))

plugins.register('Host', Host)


def test_functionality():
    host1 = Host(Munch.fromDict(host_config_example1))
    host2 = Host(Munch.fromDict(host_config_example2))
    host3 = Host(Munch.fromDict(host_config_example3))
    host4 = Host.from_args('0.0.0.0', 'user', 'pass')
    host5 = Host.from_args('0.0.0.0', 'user', pem_path='/path/to/pem')
