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


def ftp_preflight(host: str, username: str, password: str = "", timeout: float = 8.0, use_tls: bool = False) -> bool:
    """True only if login AND a real data-channel operation both succeed.

    Deliberately short timeout: this is meant to run before a real
    collection attempt, not replace one -- a source that can't answer within
    a few seconds should be skipped for this run, not retried at length here.
    """
    return ftp_preflight_diagnostic(host, username, password, timeout, use_tls)["ok"]


def ftp_preflight_diagnostic(
    host: str, username: str, password: str = "", timeout: float = 8.0, use_tls: bool = False
) -> dict:
    """Same check as ftp_preflight(), but returns which step it reached and
    the real exception instead of collapsing everything to a bool.

    Exists because this project has already been burned once by guessing at
    a CI-only failure instead of seeing the real error (see Victory's
    User-Agent theory, wrong, vs. the actual ConnectTimeoutError from the
    real log -- docs/sources.md). This dev sandbox can't reach GitHub
    Actions' logs directly (sign-in required even on a public repo), so
    daily_snapshot.py writes this dict to a committed file instead -- a
    file's raw content on a public repo IS readable without sign-in, unlike
    a workflow run's log output.

    `use_tls`: this is exactly how the NEXT real bug in this project got
    found instead of guessed at -- reading this file's own diagnostic output
    (data/processed/<date>/cerberus_diagnostics.json, committed by
    daily_snapshot.py) showed Dor Alon failing at "login" with a real FTP
    error (530 Secure connection required), not the generic data-channel
    timeout every other chain hit. Confirmed live: plain ftplib.FTP gets the
    same 530; ftplib.FTP_TLS logs in fine. Pass True for chains that need it
    (see etl/scrapers/publishedprices.py's CHAINS).
    """
    result = {"host": host, "username": username, "ok": False, "failed_at": None, "error": None}
    try:
        ftp = ftplib.FTP_TLS(timeout=timeout) if use_tls else ftplib.FTP(timeout=timeout)
        result["failed_at"] = "connect"
        ftp.connect(host, 21, timeout=timeout)
        result["failed_at"] = "login"
        ftp.login(user=username, passwd=password)
        if use_tls:
            ftp.prot_p()  # secure the data channel too, not just the control channel
        result["failed_at"] = "list"
        ftp.nlst("*store*")  # exercises PASV + the data connection, not just login
        ftp.quit()
        result["ok"] = True
        result["failed_at"] = None
    except ftplib.all_errors + (OSError, socket.timeout) as exc:
        # ftplib.all_errors is itself a tuple, not a single exception class --
        # concatenate rather than nest, or Python rejects the nested tuple.
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result
