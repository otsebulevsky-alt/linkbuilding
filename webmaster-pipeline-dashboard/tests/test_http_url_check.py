"""Tests for HTTP publication URL check."""

from __future__ import annotations

import io
import unittest
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

from lib.http_url_check import check_publication_url


class TestHttpUrlCheck(unittest.TestCase):
    def test_not_http(self) -> None:
        r = check_publication_url("ftp://x.com", timeout_sec=5.0)
        self.assertFalse(r["ok"])
        self.assertEqual(r["error"], "not_http")

    @patch("lib.http_url_check.urlopen")
    def test_head_ok(self, mock_open: MagicMock) -> None:
        resp = MagicMock()
        resp.getcode.return_value = 200
        resp.geturl.return_value = "https://example.com/post"
        resp.close = MagicMock()
        mock_open.return_value = resp
        r = check_publication_url("https://example.com/post", timeout_sec=5.0)
        self.assertTrue(r["ok"])
        self.assertEqual(r["status"], 200)
        mock_open.assert_called()

    @patch("lib.http_url_check.urlopen")
    def test_head_405_then_get_ok(self, mock_open: MagicMock) -> None:
        empty = io.BytesIO(b"")
        ok_resp = MagicMock()
        ok_resp.getcode.return_value = 200
        ok_resp.geturl.return_value = "https://x.com/a"
        ok_resp.close = MagicMock()
        mock_open.side_effect = [
            HTTPError("https://x.com/a", 405, "NA", hdrs=None, fp=empty),
            ok_resp,
        ]
        r = check_publication_url("https://x.com/a", timeout_sec=5.0)
        self.assertTrue(r["ok"])
        self.assertEqual(mock_open.call_count, 2)
        empty.close()


if __name__ == "__main__":
    unittest.main()
