"""Loaded through PYTHONPATH by the self-check, into every Python process it starts, children included.

MC4_GUARD_NET=1: any socket call to a non-loopback address is logged to MC4_GUARD_LOG and refused.
MC4_GUARD_NO_TORCH=1: importing torch or transformers is logged and refused. Set on query processes.
"""

import ipaddress
import os
import socket
import sys

LOG = os.environ.get("MC4_GUARD_LOG")


def _record(kind, detail):
    if LOG:
        with open(LOG, "a", encoding="utf-8") as out:
            out.write(f"{kind} {detail} pid={os.getpid()}\n")


def _loopback(host):
    if host in ("localhost", ""):
        return True
    try:
        return ipaddress.ip_address(str(host).split("%", 1)[0]).is_loopback
    except ValueError:
        return False


if os.environ.get("MC4_GUARD_NET") == "1":
    _connect, _connect_ex, _sendto, _getaddrinfo = socket.socket.connect, socket.socket.connect_ex, socket.socket.sendto, socket.getaddrinfo

    def _check(sock, address):
        if sock.family in (socket.AF_INET, socket.AF_INET6) and not _loopback(address[0]):
            _record("network", address)
            raise PermissionError(f"self-check guard: non-loopback socket refused: {address}")

    def connect(self, address):
        _check(self, address)
        return _connect(self, address)

    def connect_ex(self, address):
        _check(self, address)
        return _connect_ex(self, address)

    def sendto(self, *args):
        _check(self, args[-1])
        return _sendto(self, *args)

    def getaddrinfo(host, *args, **kwargs):
        if not _loopback(host):
            _record("dns", host)
            raise socket.gaierror(f"self-check guard: name lookup refused: {host}")
        return _getaddrinfo(host, *args, **kwargs)

    socket.socket.connect, socket.socket.connect_ex, socket.socket.sendto, socket.getaddrinfo = connect, connect_ex, sendto, getaddrinfo


if os.environ.get("MC4_GUARD_NO_TORCH") == "1":

    class _NoTorch:
        @staticmethod
        def find_spec(name, path=None, target=None):
            if name.split(".")[0] in ("torch", "transformers"):
                _record("import", name)
                raise ImportError(f"self-check guard: {name} must not load in a query process")
            return None

    sys.meta_path.insert(0, _NoTorch)
