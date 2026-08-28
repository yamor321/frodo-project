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

from etl.health_check import ftp_preflight, ftp_preflight_diagnostic


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


class FtpPreflightDiagnosticTests(unittest.TestCase):
    """Exists so a real CI failure can be understood from a committed file
    instead of guessed at -- these prove `failed_at` names the actual step
    reached, not just pass/fail."""

    @patch("etl.health_check.ftplib.FTP")
    def test_success_reports_ok_with_no_failed_step(self, mock_ftp_class):
        mock_ftp_class.return_value = MagicMock()
        result = ftp_preflight_diagnostic("example.com", "user", "pass")
        self.assertEqual(result, {"host": "example.com", "username": "user", "ok": True, "failed_at": None, "error": None})

    @patch("etl.health_check.ftplib.FTP")
    def test_connect_failure_reports_connect_step(self, mock_ftp_class):
        mock_ftp = MagicMock()
        mock_ftp.connect.side_effect = TimeoutError("connect timed out")
        mock_ftp_class.return_value = mock_ftp

        result = ftp_preflight_diagnostic("example.com", "user", "pass")
        self.assertFalse(result["ok"])
        self.assertEqual(result["failed_at"], "connect")
        self.assertIn("TimeoutError", result["error"])

    @patch("etl.health_check.ftplib.FTP")
    def test_login_failure_reports_login_step(self, mock_ftp_class):
        mock_ftp = MagicMock()
        mock_ftp.login.side_effect = OSError("connection refused")
        mock_ftp_class.return_value = mock_ftp

        result = ftp_preflight_diagnostic("example.com", "user", "pass")
        self.assertEqual(result["failed_at"], "login")
        self.assertIn("connection refused", result["error"])

    @patch("etl.health_check.ftplib.FTP")
    def test_data_channel_failure_reports_list_step(self, mock_ftp_class):
        """The exact shape this project hit in its own dev sandbox --
        distinguishing this from a login failure is the whole point."""
        import socket

        mock_ftp = MagicMock()
        mock_ftp.nlst.side_effect = socket.timeout("timed out")
        mock_ftp_class.return_value = mock_ftp

        result = ftp_preflight_diagnostic("example.com", "user", "pass")
        self.assertEqual(result["failed_at"], "list")


if __name__ == "__main__":
    unittest.main()
