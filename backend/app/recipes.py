"""Recipe loading and validation utilities with includes/extends/env and incremental validation."""
from __future__ import annotations
import os
import glob
import time
import threading
import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Iterable, Any, Set
from pathlib import Path

import yaml
from pydantic import BaseModel, ValidationError, Field
from dotenv import dotenv_values

logger = logging.getLogger("prompt_console")


class RecipeModel(BaseModel):
    id: str
    assistant: str
    category: str
    operators: List[str]
    hparams: Dict[str, object]
    guards: Dict[str, object] = Field(default_factory=dict)
    examples: List[str] = Field(default_factory=list)
    # Optional metadata (non-breaking)
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    version: Optional[str] = None


@dataclass
class RecipeError:
    file_path: str
    error: str
    error_type: str  # yaml_parse | schema_validation | semantic_validation | cross_file_validation | io_error | unknown
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


# Recursive scanning support for recipes subdirectories
RECIPES_RECURSIVE = os.getenv("RECIPES_RECURSIVE", "0") == "1"

# Optional validation scope: controls when semantic warnings exclude recipes under strict mode
# Defaults preserve existing behavior (exclude for all categories when strict=1)
VALIDATION_STRICT_SCOPE_DEFAULT = "all"


def _strict_filter_applies(category: str, strict: bool, scope: str) -> bool:
    """Return True if semantic-invalid recipes should be excluded for this category.

    - If strict is False -> never exclude on semantic warnings.
    - If scope == "all" -> exclude for all categories.
    - If scope == "critical" -> exclude only for critical categories (law/medical).
    """
    if not strict:
        return False
    scope = (scope or VALIDATION_STRICT_SCOPE_DEFAULT).lower()
    if scope == "critical":
        return category in {"law", "medical"}
    return True


def load_recipes(recipes_dir: str) -> Tuple[List[RecipeModel], List[RecipeError]]:
    """One-shot load using RecipesCache for convenience."""
    cache = RecipesCache(recipes_dir)
    return cache.ensure_loaded(force=True)


def validate_recipe(recipe: RecipeModel) -> List[str]:
    """Additional semantic validations beyond Pydantic schema."""
    issues: List[str] = []
    # Enforce known enums
    known_assistants = {"chatgpt", "claude", "gemini", "deepseek"}
    known_categories = {"coding", "science", "psychology", "law", "politics"}
    if recipe.assistant not in known_assistants:
        issues.append(f"unknown assistant '{recipe.assistant}'")
    if recipe.category not in known_categories:
        issues.append(f"unknown category '{recipe.category}'")
    # Required operators list must not be empty
    if not recipe.operators:
        issues.append("operators list must not be empty")
    # Domain caps per tech spec
    category_caps = {
        "law": 0.3,
        "medical": 0.3,
        "psychology": 0.35,
        "politics": 0.35,
        "science": 0.4,
        "coding": 0.4,
    }
    cap = category_caps.get(recipe.category)
    if cap is not None:
        max_temp = recipe.guards.get("max_temperature") if isinstance(recipe.guards, dict) else None
        try:
            if max_temp is None:
                # In legacy tests, absence was acceptable; do not emit an issue here
                pass
            else:
                # Only error if numeric and exceeds cap
                if float(max_temp) > float(cap):
                    issues.append(f"{recipe.category} requires guards.max_temperature ≤ {cap}")
        except Exception:
            issues.append("guards.max_temperature must be a number")
    return issues


def filter_recipes(recipes: List[RecipeModel], assistant: str, category: str) -> Tuple[List[RecipeModel], str, List[str]]:
    """Return candidates with explicit fallback tiers and notes.

    Tiers (first non-empty wins):
      1) assistant + category
      2) assistant + baseline (recipe id endswith ".baseline")
      3) assistant + any category
      4) any assistant + category
      5) any assistant + any category
    """
    notes: List[str] = []
    tier = ""
    # Tier 1: exact match
    tier1 = [r for r in recipes if r.assistant == assistant and r.category == category]
    if tier1:
        tier = "assistant+category"
        notes.append("tier=assistant+category")
        return tier1, tier, notes
    # Tier 2: assistant baseline
    tier2 = [r for r in recipes if r.assistant == assistant and r.id.endswith(".baseline")]
    if tier2:
        tier = "assistant+baseline"
        notes.append("tier=assistant+baseline")
        return [tier2[0]], tier, notes
    # Tier 3: assistant any category
    tier3 = [r for r in recipes if r.assistant == assistant]
    if tier3:
        tier = "assistant+any"
        notes.append("tier=assistant+any")
        return [tier3[0]], tier, notes
    # Tier 4: any assistant with category
    tier4 = [r for r in recipes if r.category == category]
    if tier4:
        tier = "any+category"
        notes.append("tier=any+category")
        return [tier4[0]], tier, notes
    # Tier 5: any
    if recipes:
        tier = "any+any"
        notes.append("tier=any+any")
        return [recipes[0]], tier, notes
    # None
    return [], "none", notes


class RecipesCache:
    def __init__(self, recipes_dir: str) -> None:
        self.recipes_dir = os.path.abspath(recipes_dir)
        self._recipes: List[RecipeModel] = []
        self._errors: List[RecipeError] = []
        self._mtimes: Dict[str, int] = {}
        self._last_loaded_ns: int = 0
        self._lock = threading.Lock()
        # Advanced state
        self._raw_docs_by_file: Dict[str, Any] = {}
        self._defines_by_file: Dict[str, List[str]] = {}
        self._includes_by_file: Dict[str, List[str]] = {}
        self._id_to_file: Dict[str, str] = {}
        self._id_graph: Dict[str, List[str]] = {}
        self._id_graph_rev: Dict[str, Set[str]] = {}
        self._compiled_by_id: Dict[str, Dict[str, Any]] = {}
        self._last_known_good_by_id: Dict[str, Dict[str, Any]] = {}
        # Env
        self._env_loaded = False
        self._env_values: Dict[str, str] = {}
        self._env_whitelist: Set[str] = set()

    def snapshot(self) -> Tuple[List[RecipeModel], List[RecipeError]]:
        return list(self._recipes), list(self._errors)

    def _scan_files(self) -> List[str]:
        if RECIPES_RECURSIVE:
            return sorted(glob.glob(os.path.join(self.recipes_dir, "**", "*.yaml"), recursive=True))
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
        return changed or (not self._recipes and bool(files))

    # ---------- Env handling ----------
    def _load_env_once(self) -> None:
        if self._env_loaded:
            return
        wl = os.getenv("ENV_WHITELIST", "")
        if wl:
            self._env_whitelist = {s.strip() for s in wl.split(',') if s.strip()}
        # Look for .env in repo root or recipes dir
        repo_root = Path(self.recipes_dir).parent.parent
        for cand in [repo_root / ".env", Path(self.recipes_dir) / ".env"]:
            try:
                if cand.exists():
                    vals = dotenv_values(str(cand))
                    self._env_values = {k: str(v) for k, v in vals.items() if isinstance(v, (str, int, float))}
                    break
            except Exception:
                pass
        self._env_loaded = True

    _ENV_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")

    def _apply_env_substitution(self, obj: Any, file_path: str, rid: Optional[str], strict: bool, collect_errors: List[RecipeError]) -> Any:
        def subst(s: str) -> str:
            def repl(m: re.Match[str]) -> str:
                var = m.group(1)
                if var not in self._env_whitelist:
                    return m.group(0)
                val = os.getenv(var)
                if val is None:
                    val = self._env_values.get(var)
                if val is None:
                    collect_errors.append(RecipeError(file_path=file_path, error=f"ENV var {var} not set for recipe {rid or ''}", error_type="semantic_validation", line_number=None))
                    return m.group(0)
                return str(val)
            return self._ENV_RE.sub(repl, s)
        if isinstance(obj, str):
            return subst(obj)
        if isinstance(obj, list):
            return [self._apply_env_substitution(x, file_path, rid, strict, collect_errors) for x in obj]
        if isinstance(obj, dict):
            return {k: self._apply_env_substitution(v, file_path, rid, strict, collect_errors) for k, v in obj.items()}
        return obj

    # ---------- Helpers ----------
    @staticmethod
    def _deep_merge(base: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
        out: Dict[str, Any] = dict(base)
        for k, v in overlay.items():
            if isinstance(v, dict) and isinstance(out.get(k), dict):
                out[k] = RecipesCache._deep_merge(out[k], v)
            else:
                out[k] = v
        return out

    @staticmethod
    def _dedupe_preserve_order(items: List[Any]) -> List[Any]:
        seen: Set[Any] = set()
        out: List[Any] = []
        for x in items:
            if x not in seen:
                seen.add(x)
                out.append(x)
        return out

    def _apply_operators_plus(self, merged: Dict[str, Any]) -> None:
        ops_plus = merged.pop("operators+", None)
        if ops_plus is None:
            return
        base_ops = merged.get("operators", [])
        if not isinstance(base_ops, list):
            base_ops = []
        if isinstance(ops_plus, list):
            merged["operators"] = self._dedupe_preserve_order(list(base_ops) + list(ops_plus))

    def _validate_fragment_schema(self, frag: Dict[str, Any], frag_file: str, ref_file: str, collect_errors: List[RecipeError]) -> bool:
        illegal = set(frag.keys()) - {"operators", "hparams", "guards", "examples"}
        if illegal:
            collect_errors.append(RecipeError(file_path=frag_file, error=f"fragment contains illegal keys: {sorted(illegal)} (referenced from {ref_file})", error_type="schema_validation", line_number=None))
            return False
        return True

    @staticmethod
    def _detect_cycles(graph: Dict[str, List[str]]) -> List[List[str]]:
        cycles: List[List[str]] = []
        temp: Set[str] = set()
        perm: Set[str] = set()
        stack: List[str] = []

        def visit(n: str):
            if n in perm:
                return
            if n in temp:
                if n in stack:
                    i = stack.index(n)
                    cycles.append(stack[i:] + [n])
                return
            temp.add(n)
            stack.append(n)
            for m in graph.get(n, []):
                visit(m)
            stack.pop()
            temp.remove(n)
            perm.add(n)

        for node in list(graph.keys()):
            visit(node)
        return cycles

    def _build_deps_payload(self) -> Tuple[Dict[str, Dict[str, List[str]]], Dict[str, Dict[str, List[str]]]]:
        by_id: Dict[str, Dict[str, List[str]]] = {}
        for rid, parents in self._id_graph.items():
            file = self._id_to_file.get(rid, "")
            includes = self._includes_by_file.get(file, [])
            by_id[rid] = {"extends": list(parents or []), "includes": list(includes or [])}
        by_file: Dict[str, Dict[str, List[str]]] = {}
        for f, incs in self._includes_by_file.items():
            by_file[f] = {"includes": list(incs or []), "defines": self._defines_by_file.get(f, [])}
        for f, defs in self._defines_by_file.items():
            by_file.setdefault(f, {"includes": [], "defines": defs})
        return by_id, by_file

    def get_deps(self) -> Tuple[Dict[str, Dict[str, List[str]]], Dict[str, Dict[str, List[str]]]]:
        return self._build_deps_payload()

    def ensure_loaded(self, force: bool = False, reason: str = "auto") -> Tuple[List[RecipeModel], List[RecipeError]]:
        with self._lock:
            strict = os.getenv("VALIDATION_STRICT", "0") == "1"
            if not force and not self._need_reload():
                return self.snapshot()
            files = self._scan_files()
            errors: List[RecipeError] = []
            mtimes: Dict[str, int] = {}
            raw_docs: Dict[str, Any] = {}
            defines_by_file: Dict[str, List[str]] = {}
            includes_by_file: Dict[str, List[str]] = {}
            id_to_file: Dict[str, str] = {}
            duplicates: Dict[str, List[str]] = {}

            for path in files:
                data, perr = _parse_yaml(path)
                try:
                    mtimes[path] = os.stat(path).st_mtime_ns
                except FileNotFoundError:
                    mtimes[path] = 0
                if perr is not None:
                    errors.append(perr)
                    continue
                if not isinstance(data, dict):
                    errors.append(RecipeError(file_path=path, error="YAML root must be a mapping", error_type="schema_validation", line_number=None))
                    continue
                raw_docs[path] = data
                rid = data.get("id")
                if not rid:
                    # Top-level YAML without id must live under _fragments/
                    rel = Path(path).resolve().relative_to(Path(self.recipes_dir).resolve()).as_posix()
                    if "/_fragments/" not in rel and not rel.startswith("_fragments/"):
                        errors.append(RecipeError(file_path=path, error="file without 'id' must be a fragment under recipes/_fragments/", error_type="schema_validation", line_number=None))
                if rid:
                    defines_by_file.setdefault(path, []).append(str(rid))
                    if rid in id_to_file:
                        duplicates.setdefault(rid, []).append(id_to_file[rid])
                        duplicates.setdefault(rid, []).append(path)
                    else:
                        id_to_file[rid] = path
                # includes
                incs: List[str] = []
                if "include" in data:
                    inc_val = data.get("include")
                    if isinstance(inc_val, list):
                        for ent in inc_val:
                            if not isinstance(ent, str):
                                errors.append(RecipeError(file_path=path, error="include entries must be strings", error_type="schema_validation", line_number=None))
                                continue
                            # normalize and restrict under recipes_dir
                            if os.path.isabs(ent):
                                errors.append(RecipeError(file_path=path, error=f"absolute paths not allowed in include: {ent}", error_type="cross_file_validation", line_number=None))
                                continue
                            target = (Path(self.recipes_dir) / ent).resolve()
                            try:
                                target.relative_to(Path(self.recipes_dir).resolve())
                            except Exception:
                                errors.append(RecipeError(file_path=path, error=f"include escapes recipes/: {ent}", error_type="cross_file_validation", line_number=None))
                                continue
                            # restrict includes to _fragments directory
                            rel_posix = target.relative_to(Path(self.recipes_dir).resolve()).as_posix()
                            if "/_fragments/" not in rel_posix and not rel_posix.startswith("_fragments/"):
                                errors.append(RecipeError(file_path=path, error=f"include must reference _fragments/: {ent}", error_type="cross_file_validation", line_number=None))
                                continue
                            incs.append(rel_posix)
                    else:
                        errors.append(RecipeError(file_path=path, error="include must be a list of relative file paths", error_type="schema_validation", line_number=None))
                includes_by_file[path] = incs

            # Build id graph from extends
            id_graph: Dict[str, List[str]] = {}
            id_graph_rev: Dict[str, Set[str]] = {}
            for path, data in raw_docs.items():
                rid = data.get("id")
                if not rid:
                    continue
                parents: List[str] = []
                if "extends" in data:
                    ext = data.get("extends")
                    if isinstance(ext, str):
                        parents = [ext]
                    elif isinstance(ext, list) and all(isinstance(x, str) for x in ext):
                        parents = list(ext)
                    else:
                        errors.append(RecipeError(file_path=path, error="extends must be string or list of strings", error_type="schema_validation", line_number=None))
                id_graph[rid] = parents
                for p in parents:
                    id_graph_rev.setdefault(p, set()).add(rid)

            # Duplicate id errors
            for rid, files_list in duplicates.items():
                uniq = sorted(set(files_list))
                errors.append(RecipeError(file_path=uniq[0], error=f"duplicate id '{rid}' defined in: {uniq}", error_type="cross_file_validation", line_number=None))

            # Extends graph cycles
            for cyc in self._detect_cycles(id_graph):
                if not cyc:
                    continue
                rid0 = cyc[0]
                f0 = id_to_file.get(rid0, next(iter(defines_by_file.keys()), self.recipes_dir))
                errors.append(RecipeError(file_path=f0, error=f"extends cycle detected: {' -> '.join(cyc)}", error_type="cross_file_validation", line_number=None))

            # Compile
            self._load_env_once()
            compiled_by_id: Dict[str, Dict[str, Any]] = {}
            out_models: List[RecipeModel] = []

            # Toposort
            indeg: Dict[str, int] = {n: 0 for n in id_graph.keys()}
            for n, parents in id_graph.items():
                for p in parents:
                    indeg[n] = indeg.get(n, 0) + 1
            queue: List[str] = [n for n, d in indeg.items() if d == 0]
            for rid, f in id_to_file.items():
                if rid not in indeg:
                    queue.append(rid)
                    indeg[rid] = 0
            visited: Set[str] = set()
            order: List[str] = []
            while queue:
                n = queue.pop(0)
                if n in visited:
                    continue
                visited.add(n)
                order.append(n)
                for child in id_graph_rev.get(n, set()):
                    indeg[child] = max(0, indeg.get(child, 1) - 1)
                    if indeg.get(child, 0) == 0:
                        queue.append(child)

            def in_cycle(rid: str) -> bool:
                return indeg.get(rid, 0) > 0

            # Helper: read fragment and validate
            def read_fragment(rel: str, ref_file: str) -> Optional[Dict[str, Any]]:
                abs_path = (Path(self.recipes_dir) / rel)
                if not abs_path.exists():
                    errors.append(RecipeError(file_path=ref_file, error=f"include not found: {rel}", error_type="cross_file_validation", line_number=None))
                    return None
                frag_data, perr = _parse_yaml(str(abs_path))
                if perr is not None:
                    errors.append(perr)
                    return None
                if not isinstance(frag_data, dict):
                    errors.append(RecipeError(file_path=str(abs_path), error="fragment YAML root must be a mapping", error_type="schema_validation", line_number=None))
                    return None
                if not self._validate_fragment_schema(frag_data, str(abs_path), ref_file, errors):
                    return None
                return frag_data

            for rid in order:
                if rid in duplicates:
                    continue
                file_path = id_to_file.get(rid)
                if not file_path:
                    continue
                raw = raw_docs.get(file_path, {})
                merged: Dict[str, Any] = {}
                block_errors = False
                # parents
                for parent in id_graph.get(rid, []):
                    if parent in compiled_by_id:
                        merged = self._deep_merge(merged, compiled_by_id[parent])
                    else:
                        errors.append(RecipeError(file_path=file_path, error=f"missing parent id '{parent}'", error_type="cross_file_validation", line_number=None))
                        if strict:
                            block_errors = True
                # includes
                for rel in includes_by_file.get(file_path, []):
                    frag = read_fragment(rel, file_path)
                    if frag is None:
                        if strict:
                            block_errors = True
                        continue
                    merged = self._deep_merge(merged, frag)
                # self
                merged = self._deep_merge(merged, {k: v for k, v in raw.items() if k not in ("include", "extends")})
                self._apply_operators_plus(merged)
                merged = self._apply_env_substitution(merged, file_path=file_path, rid=rid, strict=strict, collect_errors=errors)
                # operator whitelist validation
                allowed_ops = {"role_hdr", "constraints", "io_format", "examples", "quality_bar"}
                ops_val = merged.get("operators", [])
                if isinstance(ops_val, list):
                    for op in ops_val:
                        if not isinstance(op, str) or op not in allowed_ops:
                            errors.append(RecipeError(file_path=file_path, error=f"unknown operator '{op}'", error_type="schema_validation", line_number=None))
                            if strict:
                                block_errors = True

                # Build model input
                model_input = {
                    "id": merged.get("id"),
                    "assistant": merged.get("assistant"),
                    "category": merged.get("category"),
                    "operators": merged.get("operators", []),
                    "hparams": merged.get("hparams", {}),
                    "guards": merged.get("guards", {}),
                    "examples": merged.get("examples", []),
                }
                # id prefix consistency: enforce only when id's first two segments look like valid assistant/category
                id_val = model_input.get("id")
                asst = model_input.get("assistant")
                cat = model_input.get("category")
                if isinstance(id_val, str) and id_val.count(".") >= 2:
                    parts = id_val.split(".")
                    known_assistants = {"chatgpt", "claude", "gemini", "deepseek"}
                    known_categories = {"coding", "science", "psychology", "law", "politics"}
                    if parts[0] in known_assistants and parts[1] in known_categories:
                        if parts[0] != asst or parts[1] != cat:
                            errors.append(RecipeError(file_path=file_path, error=f"assistant/category fields must match id prefix: {id_val}", error_type="semantic_validation", line_number=None))
                            if strict:
                                block_errors = True
                # extends assistant/category compatibility
                for parent in id_graph.get(rid, []):
                    pfile = id_to_file.get(parent)
                    if pfile and parent in compiled_by_id:
                        p = compiled_by_id[parent]
                        pa, pc = p.get("assistant"), p.get("category")
                        if pa and pc and (pa != asst or pc != cat):
                            errors.append(RecipeError(file_path=file_path, error=f"extends parent '{parent}' assistant/category mismatch", error_type="cross_file_validation", line_number=None))
                            if strict:
                                block_errors = True
                try:
                    model = RecipeModel(**model_input)
                except ValidationError as e:
                    errors.append(RecipeError(file_path=file_path, error=str(e), error_type="schema_validation", line_number=None))
                    continue
                # examples file refs validation
                for ex in list(model.examples or []):
                    if isinstance(ex, str) and ("/" in ex or ex.startswith("./") or ex.endswith((".txt", ".md", ".yaml", ".yml"))):
                        abs_ex = (Path(self.recipes_dir) / ex).resolve()
                        try:
                            abs_ex.relative_to(Path(self.recipes_dir).resolve())
                        except Exception:
                            errors.append(RecipeError(file_path=file_path, error=f"examples reference escapes recipes/: {ex}", error_type="cross_file_validation", line_number=None))
                            if strict:
                                block_errors = True
                            continue
                        if not abs_ex.exists():
                            errors.append(RecipeError(file_path=file_path, error=f"examples reference not found: {ex}", error_type="cross_file_validation", line_number=None))
                            if strict:
                                block_errors = True
                # semantics
                for msg in validate_recipe(model):
                    errors.append(RecipeError(file_path=file_path, error=msg, error_type="semantic_validation", line_number=None))
                    if strict:
                        block_errors = True
                if in_cycle(rid):
                    errors.append(RecipeError(file_path=file_path, error=f"recipe '{rid}' is part of an extends cycle", error_type="cross_file_validation", line_number=None))
                    if strict:
                        block_errors = True
                if block_errors:
                    if not strict and rid in self._last_known_good_by_id:
                        compiled_by_id[rid] = self._last_known_good_by_id[rid]
                        try:
                            out_models.append(RecipeModel(**compiled_by_id[rid]))
                        except Exception:
                            pass
                else:
                    compiled_by_id[rid] = model_input
                    self._last_known_good_by_id[rid] = model_input
                    out_models.append(model)

            # Swap state
            if out_models:
                self._recipes = out_models
                self._mtimes = mtimes
                self._raw_docs_by_file = raw_docs
                self._defines_by_file = defines_by_file
                self._includes_by_file = includes_by_file
                self._id_to_file = id_to_file
                self._id_graph = id_graph
                self._id_graph_rev = id_graph_rev
                self._compiled_by_id = compiled_by_id
            self._errors = errors
            self._last_loaded_ns = time.time_ns()
            return self.snapshot()


def hot_reload_needed(changed_paths: List[str]) -> bool:
    return any(p.endswith(".yaml") for p in changed_paths)

