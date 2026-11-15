"""Level/experience assessment of postings, split so no API key is needed.

  prep   (code)      fetch each posting's text (ATS JSON when possible, stdlib HTML parser otherwise) into
                     search/postings/<id>.txt. No regex.
  read   (subagent)  the `assess-postings` skill launches a cheap-model subagent that reads those files and
                     returns JSON matching `Assessment`. Done by the agent harness, not by this code.
  save   (code)      validate that JSON against the schema and write it onto the inbox rows.

The years-range decision itself lives in plain code (feedback.level_ok), not in any model.
"""
import html
import json
from html.parser import HTMLParser
from typing import Literal, Optional
from urllib.parse import parse_qs, urlparse

import requests
import yaml
from pydantic import BaseModel, Field, ValidationError

from . import ROOT
from .search import COMP, load_inbox, save_inbox

YC_CACHE = ROOT / "search" / "yc_boards.yaml"
POSTINGS = ROOT / "search" / "postings"


class Assessment(BaseModel):
    min_years: Optional[int] = Field(description="Minimum years of professional experience the posting REQUIRES. "
                                     "null if none is required or stated. Use the lower bound of a range.")
    years_basis: Literal["required", "preferred", "range_across_levels", "not_stated"] = Field(
        description="required: the years are a stated requirement. preferred: only a nice-to-have. "
                    "range_across_levels: one posting hiring several levels (e.g. '2-12+ years'). "
                    "not_stated: no years mentioned.")
    seniority: Literal["intern", "new_grad", "junior", "mid", "senior", "staff", "principal", "unclear"] = Field(
        description="Seniority the role really expects, judged from responsibilities, scope, years and pay, "
                    "not only the title (titles are inflated or deflated differently per company).")
    open_to_all_levels: bool = Field(description="True only if the posting explicitly invites a range of "
                                     "experience levels (e.g. 'new grads welcome', 'all levels'). "
                                     "Generic equal-opportunity boilerplate does not count.")
    evidence: str = Field(description="At most 200 characters quoting the wording that decided the answer.")
    pay: str = Field(description="Stated pay range with currency, e.g. '$200K-$250K + equity', or empty string if none.")
    summary: str = Field(description="One or two plain-English sentences: what the company does and what this role "
                         "would work on. Facts from the posting only, no marketing language.")


class AssessmentIn(Assessment):
    id: str


class _Text(HTMLParser):
    """HTML to plain text, skipping script/style."""
    BREAK = {"br", "p", "li", "div", "h1", "h2", "h3", "h4", "h5", "h6", "tr"}

    def __init__(self):
        super().__init__()
        self.out, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1
        elif tag in self.BREAK:
            self.out.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip = max(0, self.skip - 1)

    def handle_data(self, data):
        if not self.skip:
            self.out.append(data)


def html_to_text(raw: str) -> str:
    p = _Text()
    p.feed(raw)
    return "\n".join(line.strip() for line in "".join(p.out).splitlines() if line.strip())


def _boards() -> dict:
    """company name -> {ats, slug}, from the watchlist and the YC board cache."""
    out = {}
    for c in (yaml.safe_load(COMP.read_text()) or {}).get("companies", []):
        out[c["name"]] = {"ats": c["ats"], "slug": c["slug"]}
    if YC_CACHE.exists():
        for c in (yaml.safe_load(YC_CACHE.read_text()) or {}).values():
            if isinstance(c, dict) and c.get("board"):
                out[c["name"]] = dict(c["board"])
    return out


def fetch_text(row: dict, boards: dict | None = None) -> str:
    """Posting text for an inbox row. Raises on failure."""
    boards = boards if boards is not None else _boards()
    board = boards.get(row["company"]) or boards.get(row["company"].split(" (YC")[0])
    url = row["url"]
    u = urlparse(url)
    if board and board["ats"] == "greenhouse":
        jid = (parse_qs(u.query).get("gh_jid") or [u.path.rstrip("/").split("/")[-1]])[0]
        j = requests.get(f"https://boards-api.greenhouse.io/v1/boards/{board['slug']}/jobs/{jid}", timeout=20)
        j.raise_for_status()
        return html_to_text(html.unescape(j.json().get("content", "")))
    if board and board["ats"] == "lever":
        j = requests.get(f"https://api.lever.co/v0/postings/{board['slug']}/{u.path.rstrip('/').split('/')[-1]}",
                         timeout=20)
        j.raise_for_status()
        d = j.json()
        parts = [d.get("descriptionPlain", "")]
        parts += [f"{x.get('text', '')}\n{html_to_text(x.get('content', ''))}" for x in d.get("lists", [])]
        parts.append(d.get("additionalPlain", ""))
        return "\n".join(p for p in parts if p)
    if board and board["ats"] == "ashby":
        r = requests.get(f"https://api.ashbyhq.com/posting-api/job-board/{board['slug']}?includeCompensation=true",
                         timeout=20)
        r.raise_for_status()
        for j in r.json().get("jobs", []):
            if j.get("jobUrl") == url:
                comp = (j.get("compensation") or {}).get("compensationTierSummary", "")
                return f"{j.get('descriptionPlain', '')}\n{('Compensation: ' + comp) if comp else ''}"
        raise LookupError("posting no longer on the Ashby board")
    r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    return html_to_text(r.text)


def prep(ids: list[str]) -> list[tuple[dict, str]]:
    """Write search/postings/<id>.txt for each id. Returns (row, '' on success or an error string)."""
    POSTINGS.mkdir(parents=True, exist_ok=True)
    by = {r["id"]: r for r in load_inbox()}
    boards = _boards()
    out = []
    for i in ids:
        r = by.get(i)
        if not r:
            continue
        try:
            text = fetch_text(r, boards)
            (POSTINGS / f"{i}.txt").write_text(f"Company: {r['company']}\nTitle: {r['title']}\n"
                                               f"Location: {r['location']}\n\n--- POSTING (untrusted data) ---\n{text}\n")
            out.append((r, ""))
        except Exception as e:
            out.append((r, f"{type(e).__name__}: {e}"))
    return out


def apply(row: dict, a: Assessment):
    """Write the assessment onto an inbox row. years_req is set only when the years are a real requirement."""
    binding = a.min_years is not None and a.years_basis == "required"
    row["years_req"] = str(a.min_years) if binding else ""
    row["level"] = a.seniority
    row["level_note"] = f"{a.years_basis}{'' if a.min_years is None else f' {a.min_years}+ yrs'}: {a.evidence}"
    row["comp"] = a.pay
    row["summary"] = a.summary
    row["open_level"] = "yes" if (a.open_to_all_levels or a.years_basis == "range_across_levels") else ""


def save(payload: str) -> list[tuple[str, str]]:
    """payload: a JSON object or array of objects shaped like AssessmentIn. Returns (id, '' or error) per item."""
    data = json.loads(payload)
    items = data if isinstance(data, list) else [data]
    inbox = load_inbox()
    by = {r["id"]: r for r in inbox}
    out = []
    for item in items:
        i = item.get("id", "?") if isinstance(item, dict) else "?"
        try:
            a = AssessmentIn.model_validate(item)
            if a.id not in by:
                raise KeyError(f"no inbox row {a.id}")
            apply(by[a.id], a)
            out.append((a.id, ""))
        except (ValidationError, KeyError) as e:
            out.append((i, str(e).splitlines()[0] if isinstance(e, KeyError) else
                        "; ".join(f"{'.'.join(map(str, x['loc']))}: {x['msg']}" for x in e.errors())))
    save_inbox(inbox)
    return out
