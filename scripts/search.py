"""Discover postings from public ATS board APIs (Greenhouse, Lever, Ashby)."""
import csv
import hashlib
import re
from datetime import date

import requests
import yaml

from . import ROOT, tracker

def _cfg(name):
    """User's own config if present, else the tracked example."""
    p = ROOT / "search" / f"{name}.yaml"
    return p if p.exists() else ROOT / "search" / f"{name}.example.yaml"


CRIT = _cfg("criteria")
COMP = _cfg("companies")
INBOX = ROOT / "search" / "inbox.csv"
FIELDS = ["id", "company", "title", "location", "url", "source", "found", "fit_score", "fit_note", "decision"]
TIMEOUT = 20


def fetch_greenhouse(slug):
    r = requests.get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs", timeout=TIMEOUT)
    r.raise_for_status()
    for j in r.json().get("jobs", []):
        yield j["title"], (j.get("location") or {}).get("name", ""), j["absolute_url"]


def fetch_lever(slug):
    r = requests.get(f"https://api.lever.co/v0/postings/{slug}?mode=json", timeout=TIMEOUT)
    r.raise_for_status()
    for j in r.json():
        yield j["text"], (j.get("categories") or {}).get("location", ""), j["hostedUrl"]


def fetch_ashby(slug):
    r = requests.get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}", timeout=TIMEOUT)
    r.raise_for_status()
    for j in r.json().get("jobs", []):
        yield j["title"], j.get("location", ""), j["jobUrl"]


FETCHERS = {"greenhouse": fetch_greenhouse, "lever": fetch_lever, "ashby": fetch_ashby}


def loc_match(location: str, terms) -> bool:
    """Whole-word match so 'ca' hits 'San Jose, CA' but not 'Canada', 'ny' not 'Germany'."""
    return any(re.search(rf"\b{re.escape(t.lower())}\b", location.lower()) for t in terms)


def matches(title: str, location: str, c: dict) -> bool:
    t, loc = title.lower(), location.lower()
    if any(x.lower() in t for x in c.get("exclude_title", [])):
        return False
    titles = c.get("titles", [])
    if titles and not any(x.lower() in t for x in titles):
        return False
    locs = c.get("locations", [])
    if locs and not loc_match(loc, locs):
        return False
    return True


def load_inbox() -> list[dict]:
    if not INBOX.exists():
        return []
    with INBOX.open(newline="") as f:
        return list(csv.DictReader(f))


def save_inbox(rows):
    INBOX.parent.mkdir(parents=True, exist_ok=True)
    with INBOX.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def run(yc=False, refresh=False, limit=None) -> list[dict]:
    crit = yaml.safe_load(CRIT.read_text()) or {}
    companies = (yaml.safe_load(COMP.read_text()) or {}).get("companies", [])
    if yc:
        from . import yc as ycmod
        companies = companies + ycmod.discover(crit, refresh=refresh, limit=limit)
    inbox = load_inbox()
    seen = {r["url"] for r in inbox} | tracker.urls()
    new = []
    for co in companies:
        fetch = FETCHERS.get(co["ats"])
        if not fetch:
            print(f"skip {co['name']}: unknown ats {co['ats']}")
            continue
        try:
            postings = list(fetch(co["slug"]))
        except Exception as e:  # keep going on one bad board
            print(f"error {co['name']}: {e}")
            continue
        for title, loc, url in postings:
            if url in seen or not matches(title, loc, crit):
                continue
            seen.add(url)
            new.append(dict(id=hashlib.sha1(url.encode()).hexdigest()[:8], company=co["name"], title=title,
                            location=loc, url=url, source=co["ats"], found=date.today().isoformat(),
                            fit_score="", fit_note="", decision="new"))
    if new:
        save_inbox(inbox + new)
    return new
