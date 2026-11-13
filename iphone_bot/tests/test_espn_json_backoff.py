import io
import json
import unittest
from unittest.mock import patch
from iphone_bot.capture_live_research import get

class FakeResponse:
    def __init__(self,body,content_type):
        self.body=body
        self.headers={"Content-Type":content_type}
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def read(self,n=-1):return self.body

class ESPNTransportResilience(unittest.TestCase):
    @patch("iphone_bot.capture_live_research.time.sleep")
    @patch("iphone_bot.capture_live_research.urllib.request.urlopen")
    def test_html_interstitial_then_valid_json_recovers(self,open_url,sleep):
        open_url.side_effect=[
            FakeResponse(b"<!doctype html><title>temporarily unavailable</title>","text/html"),
            FakeResponse(json.dumps({"events":[]}).encode(),"application/json")]
        result=get("/scoreboard?dates=20261109")
        self.assertEqual(result,{"events":[]})
        self.assertEqual(open_url.call_count,2)
    @patch("iphone_bot.capture_live_research.time.sleep")
    @patch("iphone_bot.capture_live_research.urllib.request.urlopen")
    def test_three_bad_responses_fail_visibly_and_preserve_previous_snapshot(self,open_url,sleep):
        open_url.return_value=FakeResponse(b"<html>blocked</html>","text/html")
        with self.assertRaisesRegex(RuntimeError,"ESPN_JSON_FETCH_FAILED"):
            get("/scoreboard?dates=20261109")
        self.assertEqual(open_url.call_count,3)
    @patch("iphone_bot.capture_live_research.time.sleep")
    @patch("iphone_bot.capture_live_research.urllib.request.urlopen")
    def test_empty_or_nonobject_does_not_masquerade_as_empty_scoreboard(self,open_url,sleep):
        open_url.side_effect=[FakeResponse(b"", "application/json"),
            FakeResponse(b"[]","application/json"),
            FakeResponse(b'{"events":[]}',"application/json")]
        self.assertEqual(get("/scoreboard"),{"events":[]})
        self.assertEqual(open_url.call_count,3)

if __name__=="__main__":unittest.main()
