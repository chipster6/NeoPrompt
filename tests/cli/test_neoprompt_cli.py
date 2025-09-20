import subprocess, sys

def test_neoprompt_help():
    cmd = [sys.executable, "-m", "backend.cli.neoprompt", "--help"]
    out = subprocess.check_output(cmd, text=True)
    assert "NeoPrompt CLI" in out
    assert "choose" in out
