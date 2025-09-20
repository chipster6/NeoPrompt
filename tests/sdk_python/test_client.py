from neoprompt import Client

class DummyResp:
    def __init__(self, json_data, status_code=200):
        self._json = json_data
        self.status_code = status_code
    def raise_for_status(self):
        if not (200 <= self.status_code < 300):
            raise AssertionError("HTTP error")
    def json(self):
        return self._json


def test_client_builds(monkeypatch):
    # Monkeypatch httpx.Client.request used inside Client._request
    def fake_request(self, method, url, **kwargs):
        if url == "/healthz" and method == "GET":
            return DummyResp({"ok": True})
        if url == "/choose" and method == "POST":
            return DummyResp({"id": "1", "engineered_prompt": "ok"})
        return DummyResp({}, 200)

    monkeypatch.setattr("httpx.Client.request", fake_request)
    with Client(base_url="http://example/api") as c:
        assert c.health()["ok"] is True
        resp = c.choose("a", "b", "raw")
        assert "engineered_prompt" in resp
