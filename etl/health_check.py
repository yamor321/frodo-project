"""Cheap pre-flight checks: verify a source is actually reachable BEFORE
attempting a real collection, so a source that can't work this run gets
skipped in seconds instead of discovered the hard way after a real listing/
download attempt hangs or times out.

This generalizes a lesson learned twice in this project, in opposite
directions: Victory's laibcatalog.co.il turned out to be a TCP connect
timeout from GitHub Actions specifically (see etl/scrapers/victory.py), and
publishedprices.co.il's FTP data channel turned out to be blocked from this
dev sandbox specifically (control channel/login fine, LIST/RETR never
completes -- see etl/scrapers/publishedprices.py) -- while looking
completely healthy by a login-only check. A real pre-flight has to exercise
the actual failure-prone step (the data channel, not just the handshake),
or it doesn't catch what actually breaks in practice.
"""
from __future__ import annotations

import ftplib
import socket


def ftp_preflight(host: str, username: str, password: str = "", timeout: float = 8.0) -> bool:
    """True only if login AND a real data-channel operation both succeed.

    Deliberately short timeout: this is meant to run before a real
    collection attempt, not replace one -- a source that can't answer within
    a few seconds should be skipped for this run, not retried at length here.
    """
    try:
        ftp = ftplib.FTP(timeout=timeout)
        ftp.connect(host, 21, timeout=timeout)
        ftp.login(user=username, passwd=password)
        ftp.nlst("*store*")  # exercises PASV + the data connection, not just login
        ftp.quit()
        return True
    except ftplib.all_errors + (OSError, socket.timeout):
        # ftplib.all_errors is itself a tuple, not a single exception class --
        # concatenate rather than nest, or Python rejects the nested tuple.
        return False
