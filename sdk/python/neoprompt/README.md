# NeoPrompt Python SDK (stub)

Note: The SDK is migrating to the V2 engine endpoints (/engine/*) and CLI workflows described in NeoPrompt_TechSpecV2.md. Current examples may reflect legacy v1 and will be updated.

Local install (editable):

```bash
pip install -e sdk/python/neoprompt
```

Usage:

```python
from neoprompt import Client
with Client() as c:
    print(c.health())
    resp = c.choose("default", "general", "Hello", enhance=True)
    did = resp.get("decision_id") or resp.get("id")
    if did:
        c.feedback(did, reward=1)
```
