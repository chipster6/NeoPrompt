import os
import sys

ROOT = os.path.abspath(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Ensure the Python SDK source is importable in tests without installation
SDK_SRC = os.path.join(ROOT, "sdk", "python", "neoprompt", "src")
if os.path.isdir(SDK_SRC) and SDK_SRC not in sys.path:
    sys.path.insert(0, SDK_SRC)
