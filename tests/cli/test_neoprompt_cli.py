import subprocess, sys


def test_neoprompt_help():
    cmd = [sys.executable, "-m", "backend.cli.neoprompt", "--help"]
    out = subprocess.check_output(cmd, text=True)
    assert "NeoPrompt CLI" in out
    assert "choose" in out


def test_cli_feedback_defaults(monkeypatch):
    # Define a local DummyResp to mimic httpx responses
    class DummyResp:
        def __init__(self, json_data, status_code=200):
            self._json = json_data
            self.status_code = status_code
        def raise_for_status(self):
            if not (200 <= self.status_code < 300):
                raise AssertionError("HTTP error")
        def json(self):
            return self._json

    captured = {}

    def fake_request(self, method, url, **kwargs):
        if method == "POST" and url == "/feedback":
            captured["json"] = kwargs.get("json", {})
            return DummyResp({"ok": True})
        return DummyResp({}, 200)

    monkeypatch.setattr("httpx.Client.request", fake_request)

    # Import and invoke the CLI's main directly to avoid spawning a subprocess
    from backend.cli import neoprompt

    rc = neoprompt.main([
        "--api-base", "http://example/api",
        "feedback",
        "--decision-id", "abc",
        "--reward", "1",
    ])
    assert rc == 0
    assert captured["json"]["decision_id"] == "abc"
    assert captured["json"]["reward"] == 1.0
    assert "reward_components" in captured["json"]
    assert captured["json"]["reward_components"] == {}
