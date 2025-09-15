from backend.app.recipes import _strict_filter_applies


def test_strict_scope_all():
    assert _strict_filter_applies("coding", True, "all") is True
    assert _strict_filter_applies("law", True, "all") is True
    assert _strict_filter_applies("medical", True, "all") is True


def test_strict_scope_critical():
    # Only law/medical should be excluded when scope=critical
    assert _strict_filter_applies("coding", True, "critical") is False
    assert _strict_filter_applies("law", True, "critical") is True
    assert _strict_filter_applies("medical", True, "critical") is True


def test_strict_off_overrides_scope():
    # When strict is off, never exclude regardless of scope/category
    for scope in ("all", "critical", "anything"):
        assert _strict_filter_applies("coding", False, scope) is False
        assert _strict_filter_applies("law", False, scope) is False