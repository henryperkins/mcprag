"""
Socketpair compatibility patch for sandbox environments.

This is extracted from mcp_server_sota.py to keep compatibility logic separate.
Includes Windows-specific fixes for socket/pipe compatibility issues.
"""

import socket
import os
import asyncio
import sys
import platform
from typing import Tuple


_orig_socketpair = socket.socketpair


def _safe_socketpair(*args, **kwargs) -> Tuple[socket.socket, socket.socket]:
    """Safe socketpair implementation that falls back to TCP sockets."""
    try:
        return _orig_socketpair(*args, **kwargs)
    except OSError:
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


def _is_windows():
    """Check if running on Windows."""
    return platform.system() == "Windows" or sys.platform == "win32"


class _PipeFD:
    """File descriptor wrapper for pipe-based self-pipe."""

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
        except OSError:
            return 0


class _WindowsCompatibleEventLoop(asyncio.SelectorEventLoop):
    """Windows-compatible event loop that uses TCP sockets instead of pipes."""

    def _make_socket_self_pipe(self):
        """Create self-pipe using TCP sockets."""
        self._ssock, self._csock = _safe_socketpair()
        self._ssock.setblocking(False)
        self._csock.setblocking(False)

        def _read_from_self():
            try:
                self._ssock.recv(4096)
            except OSError:
                pass

        self._add_reader(self._ssock.fileno(), _read_from_self)

    def _make_pipe_self_pipe(self):
        """Create self-pipe using OS pipes (Unix only)."""
        rfd, wfd = os.pipe()
        os.set_blocking(rfd, False)
        os.set_blocking(wfd, False)

        def _read_from_self():
            try:
                os.read(rfd, 4096)
            except OSError:
                pass

        self._add_reader(rfd, _read_from_self)
        self._ssock = _PipeFD(rfd)
        self._csock = _PipeFD(wfd)

    def _make_self_pipe(self):
        """Create self-pipe using the best available method."""
        if _is_windows():
            # On Windows, always use TCP sockets
            try:
                self._make_socket_self_pipe()
            except Exception:
                # Fall back to default behavior
                super()._make_self_pipe()
        else:
            # On Unix-like systems, try pipes first, then sockets
            try:
                self._make_pipe_self_pipe()
            except (OSError, AttributeError):
                # Fall back to socket-based implementation
                self._make_socket_self_pipe()


class _SafeEventLoopPolicy(asyncio.DefaultEventLoopPolicy):
    """Event loop policy that uses Windows-compatible event loops."""

    def new_event_loop(self):
        return _WindowsCompatibleEventLoop()


def apply_patches():
    """Apply all compatibility patches."""
    # Patch socket.socketpair
    socket.socketpair = _safe_socketpair

    # Install safe event loop policy
    asyncio.set_event_loop_policy(_SafeEventLoopPolicy())
