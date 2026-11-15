"""Iterative job hunt (WORK IN PROGRESS: ranking is a crude heuristic, expect it to change).

Iterative job hunt: show a few candidates, record feedback, learn weights for the next hunt.

Files (all gitignored, personal):
  search/feedback.csv       append-only log of every verdict + reason
  search/preferences.yaml   learned weights + hard blocks + free-text notes (agent or user may edit)
"""
import csv
import re
from datetime import date

import yaml

from . import ROOT
from .search import CRIT, load_inbox, save_inbox

FEEDBACK = ROOT / "search" / "feedback.csv"
PREFS = ROOT / "search" / "preferences.yaml"
FB_FIELDS = ["date", "id", "company", "title", "location", "verdict", "reason"]
STEP = 0.5          # weight change per vote
CAP = 3.0           # |weight| limit so one word cannot dominate
STOP = {"and", "or", "the", "of", "for", "a", "in", "to", "engineer", "engineering", "software", "senior",
        "staff", "principal", "sr", "ii", "iii", "i", "team", "-", "/", "&", "|"}
EMPTY = {"title_words": {}, "companies": {}, "locations": {}, "block_companies": [], "block_title": [], "notes": []}


def load_prefs() -> dict:
    d = yaml.safe_load(PREFS.read_text()) if PREFS.exists() else {}
    return {**{k: type(v)() for k, v in EMPTY.items()}, **(d or {})}


def save_prefs(p: dict):
    PREFS.parent.mkdir(parents=True, exist_ok=True)
    PREFS.write_text("# Learned from feedback.csv. Weights update automatically; edit blocks/notes freely.\n"
                     + yaml.safe_dump(p, sort_keys=False, allow_unicode=True))


def words(title: str) -> set[str]:
    return {w for w in re.findall(r"[a-z][a-z+#.]*", title.lower()) if w not in STOP and len(w) > 1}


def cities(location: str) -> set[str]:
    return {c.strip().lower() for c in re.split(r"[|;]", location) if c.strip()}


def _bump(d: dict, key: str, delta: float):
    d[key] = max(-CAP, min(CAP, round(d.get(key, 0) + delta, 2)))
    if d[key] == 0:
        del d[key]


def score(row: dict, prefs: dict) -> float:
    """Agent fit_score (1-5, default 3) plus learned weights."""
    try:
        base = float(row.get("fit_score") or 3)
    except ValueError:
        base = 3.0
    s = base + prefs["companies"].get(row["company"].lower(), 0)
    s += sum(prefs["title_words"].get(w, 0) for w in words(row["title"]))
    s += sum(prefs["locations"].get(c, 0) for c in cities(row["location"]))
    return round(s, 2)


def blocked(company: str, title: str, prefs: dict) -> bool:
    return (company.lower() in {c.lower() for c in prefs["block_companies"]}
            or any(b.lower() in title.lower() for b in prefs["block_title"]))


def level_ok(row: dict, crit: dict) -> bool:
    """Plain-code decision from fields the cheap model extracted (`hj assess`).

    Unassessed rows pass, so nothing is hidden on a guess. Rows that welcome all levels or span levels pass.
    """
    if row.get("open_level"):
        return True
    yr = (row.get("years_req") or "").strip()
    rng = crit.get("years_required") or {}
    if yr:
        try:
            return rng.get("min", 0) <= float(yr) <= rng.get("max", 99)
        except ValueError:
            return True
    levels = crit.get("levels", [])
    lv = row.get("level") or ""
    return not levels or not lv or lv in levels


def batch(n: int = 5) -> list[dict]:
    """Top-n undecided inbox rows by score, blocked/out-of-level skipped. Adds 'score' and 'level' keys."""
    prefs = load_prefs()
    crit = yaml.safe_load(CRIT.read_text()) or {}
    rows = [dict(r, score=score(r, prefs)) for r in load_inbox()
            if r["decision"] == "new" and not blocked(r["company"], r["title"], prefs) and level_ok(r, crit)]
    # spread across companies: at most 2 per company per batch, so one big board doesn't flood it
    rows.sort(key=lambda r: -r["score"])
    out, per = [], {}
    for r in rows:
        if per.get(r["company"], 0) < 2:
            out.append(r)
            per[r["company"]] = per.get(r["company"], 0) + 1
        if len(out) == n:
            break
    return out


def set_level(job_id: str, years: str, note: str = "") -> dict:
    """Record the minimum years of experience a posting asks for ('' = not stated) and a short note."""
    inbox = load_inbox()
    row = next((r for r in inbox if r["id"] == job_id), None)
    if not row:
        raise KeyError(f"no inbox row {job_id}")
    if years:
        float(years)  # validate
    row["years_req"], row["level_note"] = years, note
    save_inbox(inbox)
    return row


def record(job_id: str, verdict: str, reason: str = "") -> dict:
    """verdict: like|dislike. Logs it, sets inbox decision, updates learned weights."""
    if verdict not in ("like", "dislike"):
        raise ValueError("verdict must be like or dislike")
    inbox = load_inbox()
    row = next((r for r in inbox if r["id"] == job_id), None)
    if not row:
        raise KeyError(f"no inbox row {job_id}")
    sign = 1 if verdict == "like" else -1
    prefs = load_prefs()
    _bump(prefs["companies"], row["company"].lower(), sign * STEP)
    for w in words(row["title"]):
        _bump(prefs["title_words"], w, sign * STEP)
    for c in cities(row["location"]):
        _bump(prefs["locations"], c, sign * STEP / 2)
    save_prefs(prefs)

    row["decision"] = "interested" if verdict == "like" else "skip"
    save_inbox(inbox)
    new = not FEEDBACK.exists()
    with FEEDBACK.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FB_FIELDS)
        if new:
            w.writeheader()
        w.writerow(dict(date=date.today().isoformat(), id=job_id, company=row["company"], title=row["title"],
                        location=row["location"], verdict=verdict, reason=reason))
    return row


def history() -> list[dict]:
    if not FEEDBACK.exists():
        return []
    with FEEDBACK.open(newline="") as f:
        return list(csv.DictReader(f))
