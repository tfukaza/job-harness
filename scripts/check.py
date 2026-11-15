"""Validate main/main.yaml and draft.yaml files."""
import re
from pathlib import Path

import yaml

from . import ROOT

MAIN = ROOT / "main" / "main.yaml"
PLACEHOLDER = re.compile(r"\b(TODO|TBD|XX+)\b|\bX\s*(%|percent)|lorem ipsum", re.I)
REQUIRED_SECTIONS = ["experience", "projects", "education", "skills"]


def iter_bullets(main: dict):
    """Yield (location, bullet) for every bullet, including nested `sub` bullets."""
    def walk(bullets, where):
        for b in bullets or []:
            yield where, b
            yield from walk(b.get("sub"), where)
    for e in main.get("experience", []) or []:
        for sec in e.get("sections", []) or []:
            yield from walk(sec.get("bullets"), f"{e.get('company', '?')} / {sec.get('name', '?')}")
        yield from walk(e.get("bullets"), e.get("company", "?"))
    for p in main.get("projects", []) or []:
        yield from walk(p.get("bullets"), p.get("name", "?"))


def main_ids(main: dict) -> set:
    ids = {b["id"] for _, b in iter_bullets(main) if b.get("id")}
    for sect in ("experience", "projects", "education", "other"):
        ids |= {x["id"] for x in main.get(sect, []) or [] if isinstance(x, dict) and x.get("id")}
    return ids


def check_main(path: Path = MAIN):
    """Return (errors, warnings) for the main resume."""
    errors, warnings = [], []
    if not path.exists():
        return [f"{path} not found (copy main/main.example.yaml)"], []
    try:
        main = yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError as e:
        return [f"invalid YAML: {e}"], []
    for k in REQUIRED_SECTIONS:
        if not main.get(k):
            errors.append(f"missing section: {k}")
    seen = {}
    for where, b in iter_bullets(main):
        bid, text = b.get("id"), (b.get("text") or "").strip()
        label = f"{bid or '<no id>'} ({where})"
        if not bid:
            errors.append(f"bullet without id in {where}: {text[:50]!r}")
        elif bid in seen:
            errors.append(f"duplicate id {bid}")
        seen[bid] = True
        if not text:
            errors.append(f"empty text: {label}")
        elif PLACEHOLDER.search(text):
            errors.append(f"placeholder in text: {label}: {text[:70]!r}")
        if not b.get("tags"):
            warnings.append(f"no tags: {label}")
        if b.get("note"):
            warnings.append(f"open note: {label}: {b['note'][:80]}")
    for sect in ("experience", "projects"):
        for item in main.get(sect, []) or []:
            name = item.get("company") or item.get("name") or item.get("id")
            has = any(True for w, b in iter_bullets({sect: [item]}))
            if not has:
                errors.append(f"{sect[:-1]} with no bullets: {name}")
            if item.get("note"):
                warnings.append(f"open note: {name}: {item['note'][:80]}")
    return errors, warnings


def draft_sources(node):
    """All `source` ids referenced anywhere in a draft."""
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "source" and isinstance(v, str):
                yield v
            else:
                yield from draft_sources(v)
    elif isinstance(node, list):
        for v in node:
            yield from draft_sources(v)


def check_draft(draft: dict, main_path: Path = MAIN):
    """Errors for a draft: unknown source ids against main.yaml, placeholders in text."""
    errors = []
    if main_path.exists():
        ids = main_ids(yaml.safe_load(main_path.read_text()) or {})
        for s in sorted(set(draft_sources(draft)) - ids):
            errors.append(f"source id not in main/main.yaml: {s}")
    def texts(n):
        if isinstance(n, dict):
            for k, v in n.items():
                if k == "text" and isinstance(v, str):
                    yield v
                else:
                    yield from texts(v)
        elif isinstance(n, list):
            for v in n:
                yield from texts(v)
    for t in texts(draft):
        if PLACEHOLDER.search(t):
            errors.append(f"placeholder in draft text: {t[:70]!r}")
    return errors
