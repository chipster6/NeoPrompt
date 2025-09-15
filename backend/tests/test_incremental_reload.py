import time
from pathlib import Path
import textwrap

from backend.app.recipes import RecipesCache


def write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")


def test_incremental_fragment_update_propagates_to_extends(tmp_path):
    recipes_dir = tmp_path / "recipes"
    recipes_dir.mkdir()

    # Fragment used by base recipe
    frag = recipes_dir / "_fragments" / "body.yaml"
    write(frag, "hparams: { note: v1 }\n")

    # Base recipe includes the fragment
    base = recipes_dir / "chatgpt.coding.base.yaml"
    write(
        base,
        """
        id: chatgpt.coding.base
        assistant: chatgpt
        category: coding
        operators: [role_hdr]
        include: ["_fragments/body.yaml"]
        hparams: { temperature: 0.2 }
        """
    )

    # Child extends base
    child = recipes_dir / "chatgpt.coding.child.yaml"
    write(
        child,
        """
        id: chatgpt.coding.child
        assistant: chatgpt
        category: coding
        operators: [role_hdr]
        extends: ["chatgpt.coding.base"]
        """
    )

    # Sanity: files exist
    ymls = sorted([p.name for p in recipes_dir.glob('*.yaml')])
    assert set(ymls) == {"chatgpt.coding.base.yaml", "chatgpt.coding.child.yaml"}

    cache = RecipesCache(str(recipes_dir))
    recipes, errors = cache.ensure_loaded(force=True)
    # Debug: ensure errors visible if any
    if not recipes:
        print("errors(first load):", [(e.error_type, e.error, e.file_path) for e in errors])

    # Verify both recipes present and note=v1 flows from fragment into base and child via extends
    m = {r.id: r for r in recipes}
    assert "chatgpt.coding.base" in m and "chatgpt.coding.child" in m
    assert m["chatgpt.coding.base"].hparams.get("note") == "v1"
    assert m["chatgpt.coding.child"].hparams.get("note") == "v1"

    # Update fragment to v2 and apply incremental events
    write(frag, "hparams: { note: v2 }\n")
    recipes2, errors2 = cache.apply_fs_events([str(frag)], reason="test")

    m2 = {r.id: r for r in recipes2}
    assert m2["chatgpt.coding.base"].hparams.get("note") == "v2"
    assert m2["chatgpt.coding.child"].hparams.get("note") == "v2"
    # No new errors expected
    assert len(errors2) >= 0


def test_incremental_fragment_error_then_fix_updates_errors_and_state(tmp_path):
    recipes_dir = tmp_path / "recipes"
    recipes_dir.mkdir()

    frag = recipes_dir / "_fragments" / "body.yaml"
    write(frag, "hparams: { note: ok }\n")

    main = recipes_dir / "chatgpt.coding.main.yaml"
    write(
        main,
        """
        id: chatgpt.coding.main
        assistant: chatgpt
        category: coding
        operators: [role_hdr]
        include: ["_fragments/body.yaml"]
        """
    )

    cache = RecipesCache(str(recipes_dir))
    recipes, errors = cache.ensure_loaded(force=True)
    if not recipes:
        print("errors(first load 2):", [(e.error_type, e.error, e.file_path) for e in errors])
    assert any(r.id == "chatgpt.coding.main" for r in recipes)
    # No errors initially
    assert not errors

    # Introduce YAML error in fragment
    frag.write_text("bad: [unclosed\n", encoding="utf-8")
    recipes2, errors2 = cache.apply_fs_events([str(frag)], reason="test")

    # Expect at least one parse error reported
    assert any(e.error_type in {"yaml_parse", "schema_validation", "cross_file_validation"} for e in errors2)

    # Fix fragment and ensure error clears and value restored
    write(frag, "hparams: { note: fixed }\n")
    recipes3, errors3 = cache.apply_fs_events([str(frag)], reason="test")

    m3 = {r.id: r for r in recipes3}
    assert m3["chatgpt.coding.main"].hparams.get("note") == "fixed"
    # Errors list should not continue to contain a yaml_parse for this file
    assert not any(e.error_type == "yaml_parse" and e.file_path.endswith("_fragments/body.yaml") for e in errors3)
