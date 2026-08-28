"""Tests for etl.health_check. Mocked, not live -- this module exists
specifically because a login-only check would have missed the real failure
this project hit (control channel fine, data channel blocked), so what
matters here is proving the logic handles that shape of failure, not
re-proving the live network behavior already documented in
etl/scrapers/publishedprices.py's module docstring.
"""
import pathlib
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from etl.health_check import ftp_preflight


class FtpPreflightTests(unittest.TestCase):
    @patch("etl.health_check.ftplib.FTP")
    def test_healthy_source_returns_true(self, mock_ftp_class):
        mock_ftp = MagicMock()
        mock_ftp_class.return_value = mock_ftp

        self.assertTrue(ftp_preflight("example.com", "user", "pass"))
        mock_ftp.login.assert_called_once_with(user="user", passwd="pass")
        mock_ftp.nlst.assert_called_once_with("*store*")

    @patch("etl.health_check.ftplib.FTP")
    def test_login_failure_returns_false(self, mock_ftp_class):
        mock_ftp = MagicMock()
        mock_ftp.login.side_effect = OSError("connection refused")
        mock_ftp_class.return_value = mock_ftp

        self.assertFalse(ftp_preflight("example.com", "user", "pass"))

    @patch("etl.health_check.ftplib.FTP")
    def test_data_channel_timeout_after_successful_login_returns_false(self, mock_ftp_class):
        """The exact failure shape this project hit live: login succeeds,
        the data-channel call (nlst) is what hangs/times out. A check that
        only tried login would have reported this source healthy."""
        import socket

        mock_ftp = MagicMock()
        mock_ftp.nlst.side_effect = socket.timeout("timed out")
        mock_ftp_class.return_value = mock_ftp

        self.assertFalse(ftp_preflight("example.com", "user", "pass"))
        mock_ftp.login.assert_called_once()


if __name__ == "__main__":
    unittest.main()
