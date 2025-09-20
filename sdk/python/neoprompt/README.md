# NeoPrompt Python SDK (stub)

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
