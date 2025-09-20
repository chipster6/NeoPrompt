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


def test_feedback_includes_empty_components_by_default(monkeypatch):
    captured = {}

    def fake_request(self, method, url, **kwargs):
        if method == "POST" and url == "/feedback":
            captured["json"] = kwargs.get("json", {})
            return DummyResp({"ok": True})
        return DummyResp({}, 200)

    monkeypatch.setattr("httpx.Client.request", fake_request)
    with Client(base_url="http://example/api") as c:
        resp = c.feedback("dec123", reward=1)
        assert resp == {"ok": True}
        assert captured["json"]["decision_id"] == "dec123"
        assert captured["json"]["reward"] == 1.0
        assert "reward_components" in captured["json"]
        assert captured["json"]["reward_components"] == {}


def test_feedback_includes_passed_components(monkeypatch):
    captured = {}

    def fake_request(self, method, url, **kwargs):
        if method == "POST" and url == "/feedback":
            captured["json"] = kwargs.get("json", {})
            return DummyResp({"ok": True})
        return DummyResp({}, 200)

    monkeypatch.setattr("httpx.Client.request", fake_request)
    with Client(base_url="http://example/api") as c:
        comps = {"hallucination": -0.5, "helpfulness": 1}
        c.feedback("dec456", reward=-1, components=comps)
        assert captured["json"]["decision_id"] == "dec456"
        assert captured["json"]["reward"] == -1.0
        assert captured["json"]["reward_components"] == comps
