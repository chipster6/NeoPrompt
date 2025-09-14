"""Recipe loading and validation utilities."""
from __future__ import annotations
import os
import glob
import time
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
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


@dataclass
class RecipeError:
    file_path: str
    error: str
    error_type: str  # yaml_parse | schema_validation | semantic_validation | io_error | unknown
    line_number: Optional[int] = None


def _parse_yaml(path: str) -> Tuple[Optional[dict], Optional[RecipeError]]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return data, None
    except yaml.MarkedYAMLError as e:  # type: ignore[attr-defined]
        line = getattr(getattr(e, 'problem_mark', None), 'line', None)
        return None, RecipeError(file_path=path, error=str(e), error_type="yaml_parse", line_number=(int(line) + 1) if line is not None else None)
    except yaml.YAMLError as e:
        return None, RecipeError(file_path=path, error=str(e), error_type="yaml_parse", line_number=None)
    except Exception as e:
        return None, RecipeError(file_path=path, error=str(e), error_type="io_error", line_number=None)


def load_recipes(recipes_dir: str) -> Tuple[List[RecipeModel], List[RecipeError]]:
    """Load all YAML recipe files from directory.
    Returns (valid_recipes, errors). Invalid files are excluded from results.
    """
    recipe_files = sorted(glob.glob(os.path.join(recipes_dir, "*.yaml")))
    valid: List[RecipeModel] = []
    errors: List[RecipeError] = []

    for path in recipe_files:
        data, perr = _parse_yaml(path)
        if perr is not None:
            errors.append(perr)
            continue
        try:
            recipe = RecipeModel(**(data or {}))
        except ValidationError as e:
            errors.append(RecipeError(file_path=path, error=str(e), error_type="schema_validation", line_number=None))
            continue
        # Semantic warnings (do not exclude recipe)
        sem_issues = validate_recipe(recipe)
        for msg in sem_issues:
            errors.append(RecipeError(file_path=path, error=msg, error_type="semantic_validation", line_number=None))
        valid.append(recipe)
    return valid, errors


def validate_recipe(recipe: RecipeModel) -> List[str]:
    """Additional semantic validations beyond Pydantic schema."""
    issues: List[str] = []
    # Required operators list must not be empty
    if not recipe.operators:
        issues.append("operators list must not be empty")
    if recipe.category in {"law", "medical"}:
        max_temp = recipe.guards.get("max_temperature") if isinstance(recipe.guards, dict) else None
        try:
            if max_temp is None or float(max_temp) > 0.3:
                issues.append("law/medical require guards.max_temperature ≤ 0.3")
        except Exception:
            issues.append("guards.max_temperature must be a number")
    return issues


# Simple mtime-based cache for recipes
class RecipesCache:
    def __init__(self, recipes_dir: str) -> None:
        self.recipes_dir = recipes_dir
        self._recipes: List[RecipeModel] = []
        self._errors: List[RecipeError] = []
        self._mtimes: Dict[str, int] = {}
        self._last_loaded_ns: int = 0

    def snapshot(self) -> Tuple[List[RecipeModel], List[RecipeError]]:
        return list(self._recipes), list(self._errors)

    def _scan_files(self) -> List[str]:
        return sorted(glob.glob(os.path.join(self.recipes_dir, "*.yaml")))

    def _need_reload(self) -> bool:
        files = self._scan_files()
        changed = False
        new_mtimes: Dict[str, int] = {}
        for p in files:
            try:
                m = os.stat(p).st_mtime_ns
            except FileNotFoundError:
                m = 0
            new_mtimes[p] = m
            if self._mtimes.get(p) != m:
                changed = True
        # Detect removed files
        for p in list(self._mtimes.keys()):
            if p not in new_mtimes:
                changed = True
        return changed or (not self._recipes and files)

    def ensure_loaded(self, force: bool = False) -> Tuple[List[RecipeModel], List[RecipeError]]:
        if not force and not self._need_reload():
            return self.snapshot()
        files = self._scan_files()
        valid: List[RecipeModel] = []
        errors: List[RecipeError] = []
        mtimes: Dict[str, int] = {}
        for path in files:
            data, perr = _parse_yaml(path)
            if perr is not None:
                errors.append(perr)
                continue
            try:
                model = RecipeModel(**(data or {}))
            except ValidationError as e:
                errors.append(RecipeError(file_path=path, error=str(e), error_type="schema_validation", line_number=None))
                continue
            for msg in validate_recipe(model):
                errors.append(RecipeError(file_path=path, error=msg, error_type="semantic_validation", line_number=None))
            valid.append(model)
            try:
                mtimes[path] = os.stat(path).st_mtime_ns
            except FileNotFoundError:
                mtimes[path] = 0
        # Swap in-memory state only if we have at least one valid recipe; always update errors
        if valid:
            self._recipes = valid
            self._mtimes = mtimes
        self._errors = errors
        self._last_loaded_ns = time.time_ns()
        return self.snapshot()


def hot_reload_needed(changed_paths: List[str]) -> bool:
    return any(p.endswith(".yaml") for p in changed_paths)

