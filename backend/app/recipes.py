"""Recipe loading and validation utilities."""
from __future__ import annotations
import os
import glob
from typing import Dict, List, Tuple
import yaml
from pydantic import BaseModel, ValidationError, Field


class RecipeModel(BaseModel):
    id: str
    assistant: str
    category: str
    operators: List[str]
    hparams: Dict[str, object]
    guards: Dict[str, object] = Field(default_factory=dict)
    examples: List[str] = Field(default_factory=list)


def load_recipes(recipes_dir: str) -> Tuple[List[RecipeModel], List[Tuple[str, str]]]:
    """Load all YAML recipe files from directory.
    Returns a tuple of (valid_recipes, errors) where errors is list of (file_path, error_message).
    """
    recipe_files = sorted(glob.glob(os.path.join(recipes_dir, "*.yaml")))
    valid: List[RecipeModel] = []
    errors: List[Tuple[str, str]] = []

    for path in recipe_files:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            recipe = RecipeModel(**data)
            valid.append(recipe)
        except (yaml.YAMLError, ValidationError, Exception) as e:
            errors.append((path, str(e)))
    return valid, errors


def validate_recipe(recipe: RecipeModel) -> List[str]:
    """Additional semantic validations beyond Pydantic schema."""
    issues: List[str] = []
    # Required operators order check (role_hdr should typically be first)
    if not recipe.operators:
        issues.append("operators list must not be empty")
    if recipe.category in {"law", "medical"}:
        max_temp = recipe.guards.get("max_temperature") if isinstance(recipe.guards, dict) else None
        if max_temp is None or float(max_temp) > 0.3:
            issues.append("law/medical require guards.max_temperature ≤ 0.3")
    return issues


def hot_reload_needed(changed_paths: List[str]) -> bool:
    return any(p.endswith(".yaml") for p in changed_paths)

