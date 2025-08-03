"""
Socketpair compatibility patch for sandbox environments.

This is extracted from mcp_server_sota.py to keep compatibility logic separate.
"""

import socket
import os
import asyncio
from typing import Tuple


_orig_socketpair = socket.socketpair


def _safe_socketpair(*args, **kwargs) -> Tuple[socket.socket, socket.socket]:
    """Safe socketpair implementation that falls back to TCP sockets."""
    try:
        return _orig_socketpair(*args, **kwargs)
    except PermissionError:
        # Fallback: create a pair of connected IPv4 sockets
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.bind(("127.0.0.1", 0))
        srv.listen(1)
        port = srv.getsockname()[1]

        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.setblocking(True)
        client.connect(("127.0.0.1", port))

        server_side, _ = srv.accept()
        srv.close()

        return (server_side, client)


class _PipeSelectorEventLoop(asyncio.SelectorEventLoop):
    """SelectorEventLoop variant that uses os.pipe() instead of socketpair()."""

    def _make_self_pipe(self):
        # Create a non-blocking pipe pair
        rfd, wfd = os.pipe()
        os.set_blocking(rfd, False)
        os.set_blocking(wfd, False)

        # Wrap the read end with a simple callback
        def _read_from_self():
            try:
                os.read(rfd, 4096)
            except (BlockingIOError, InterruptedError):
                pass

        self._add_reader(rfd, _read_from_self)

        # Store fds for cleanup
        class _PipeFD:
            def __init__(self, fd):
                self.fd = fd

            def fileno(self):
                return self.fd

            def close(self):
                try:
                    os.close(self.fd)
                except OSError:
                    pass

            def send(self, data):
                """Write data to the pipe."""
                try:
                    return os.write(self.fd, data)
                except (BlockingIOError, InterruptedError):
                    return 0

        self._ssock = _PipeFD(rfd)
        self._csock = _PipeFD(wfd)


class _SafeEventLoopPolicy(asyncio.DefaultEventLoopPolicy):
    """Event loop policy that uses pipe-based event loops."""

    def new_event_loop(self):
        return _PipeSelectorEventLoop()


def apply_patches():
    """Apply all compatibility patches."""
    # Patch socket.socketpair
    socket.socketpair = _safe_socketpair

    # Install safe event loop policy
    asyncio.set_event_loop_policy(_SafeEventLoopPolicy())
