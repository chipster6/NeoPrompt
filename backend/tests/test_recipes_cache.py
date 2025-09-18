import tempfile
from pathlib import Path

from backend.app.recipes import RecipesCache


def write(path: Path, content: str):
    path.write_text(content, encoding="utf-8")


def test_recipes_cache_last_known_good_and_yaml_error():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        recipes_dir = tmp_path
        f = recipes_dir / "sample.yaml"
        valid_yaml = (
            "id: test.assistant.category.baseline\n"
            "assistant: chatgpt\n"
            "category: coding\n"
            "operators: [role_hdr, constraints, io_format, quality_bar]\n"
            "hparams: { temperature: 0.2, top_p: 0.9, max_tokens: 100 }\n"
            "guards: { max_temperature: 0.4 }\n"
            "examples: []\n"
        )
        write(f, valid_yaml)

        cache = RecipesCache(str(recipes_dir))
        recipes, errors = cache.ensure_loaded(force=True)
        assert len(recipes) == 1
        assert recipes[0].id == "test.assistant.category.baseline"
        assert errors == []

        # Break the YAML
        broken_yaml = "id: broken\nassistant: chatgpt\ncategory: coding\noperators: [role_hdr\n"  # missing closing ]
        write(f, broken_yaml)

        recipes2, errors2 = cache.ensure_loaded(force=True)
        # Last good should still be served
        assert len(recipes2) == 1
        assert recipes2[0].id == "test.assistant.category.baseline"
        # An error should be reported with type yaml_parse
        assert any(e.error_type == "yaml_parse" for e in errors2), errors2