"""Find hiring YC startups and discover their public ATS boards.

Source: community-maintained dataset https://yc-oss.github.io/api (public JSON).
For each company that passes the filters, probe Ashby/Lever/Greenhouse for a board
with name-derived slugs. Results (including misses) are cached in search/yc_boards.yaml.
"""
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from urllib.parse import urlparse

import requests
import yaml

from . import ROOT

HIRING_URL = "https://yc-oss.github.io/api/companies/hiring.json"
CACHE = ROOT / "search" / "yc_boards.yaml"
TIMEOUT = 12

PROBES = {
    "ashby": "https://api.ashbyhq.com/posting-api/job-board/{s}",
    "greenhouse": "https://boards-api.greenhouse.io/v1/boards/{s}/jobs",
    "lever": "https://api.lever.co/v0/postings/{s}?mode=json",
}


def load_hiring() -> list[dict]:
    r = requests.get(HIRING_URL, timeout=60)
    r.raise_for_status()
    return r.json()


def batch_year(batch: str) -> int:
    m = re.search(r"(\d{4})", batch or "")
    return int(m.group(1)) if m else 0


def filter_companies(companies, crit: dict) -> list[dict]:
    yc = crit.get("yc", {}) or {}
    min_year = yc.get("min_batch_year", 2022)
    stages = [s.lower() for s in yc.get("stages", ["early"])]
    tags = [t.lower() for t in yc.get("tags", [])]
    skip_tags = [t.lower() for t in yc.get("exclude_tags", [])]
    locs = [x.lower() for x in crit.get("locations", [])]
    out = []
    for c in companies:
        if c.get("status") != "Active" or not c.get("isHiring"):
            continue
        if batch_year(c.get("batch", "")) < min_year:
            continue
        if stages and (c.get("stage") or "").lower() not in stages:
            continue
        loc = (c.get("all_locations") or "").lower()
        if locs and not any(x in loc for x in locs):
            continue
        ctags = [t.lower() for t in (c.get("tags") or []) + (c.get("industries") or [])]
        if tags and not any(t in ct for t in tags for ct in ctags):
            continue
        if any(t in ct for t in skip_tags for ct in ctags):
            continue
        out.append(c)
    return out


def candidate_slugs(c: dict) -> list[str]:
    names = {c["slug"], re.sub(r"[^a-z0-9]", "", c["name"].lower()), re.sub(r"[^a-z0-9]+", "-", c["name"].lower()).strip("-")}
    host = urlparse(c.get("website") or "").netloc.lower().removeprefix("www.")
    if host:
        names.add(host.split(".")[0])
    return [n for n in names if n]


def probe(c: dict):
    """Return {'ats','slug','name'} for the first board with at least one job, else None."""
    for slug in candidate_slugs(c):
        for ats, url in PROBES.items():
            try:
                r = requests.get(url.format(s=slug), timeout=TIMEOUT)
                if r.status_code != 200:
                    continue
                data = r.json()
            except Exception:
                continue
            jobs = data if isinstance(data, list) else data.get("jobs", [])
            if jobs:
                return {"ats": ats, "slug": slug}
    return None


def load_cache() -> dict:
    return (yaml.safe_load(CACHE.read_text()) or {}) if CACHE.exists() else {}


def discover(crit: dict, refresh=False, limit=None, log=print) -> list[dict]:
    """Return watchlist entries ({name, ats, slug}) for filtered YC companies."""
    cands = filter_companies(load_hiring(), crit)
    if limit:
        cands = cands[:limit]
    cache = load_cache()
    todo = [c for c in cands if refresh or c["slug"] not in cache]
    log(f"YC: {len(cands)} companies match filters, {len(todo)} to probe for job boards")
    if todo:
        with ThreadPoolExecutor(max_workers=16) as ex:
            results = list(ex.map(probe, todo))
        for c, res in zip(todo, results):
            cache[c["slug"]] = {"name": c["name"], "board": res, "checked": date.today().isoformat()}
        CACHE.write_text(yaml.safe_dump(cache, sort_keys=True))
    entries = []
    for c in cands:
        b = (cache.get(c["slug"]) or {}).get("board")
        if b:
            entries.append({"name": f"{c['name']} (YC {c.get('batch','')})", **b})
    log(f"YC: {len(entries)} of {len(cands)} have a discoverable Ashby/Lever/Greenhouse board")
    return entries
