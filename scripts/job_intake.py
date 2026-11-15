"""Create jobs/<slug>/job.md from an inbox id or URL."""
import re
from datetime import date

import requests

from . import ROOT, search


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40]


def html_to_text(html: str) -> str:
    html = re.sub(r"(?is)<(script|style).*?</\1>", "", html)
    html = re.sub(r"(?i)<br\s*/?>|</p>|</li>|</h\d>", "\n", html)
    text = re.sub(r"<[^>]+>", "", html)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def intake(target: str, company: str = "", role: str = "") -> "Path":  # noqa: F821
    url = target
    for r in search.load_inbox():
        if r["id"] == target:
            url, company, role = r["url"], r["company"], r["title"]
    body = ""
    try:
        resp = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        body = html_to_text(resp.text)
    except Exception as e:
        body = f"(fetch failed: {e}. Paste the job description here.)"
    slug = f"{date.today().isoformat()}-{slugify(company or 'company')}-{slugify(role or 'role')}"
    d = ROOT / "jobs" / slug
    d.mkdir(parents=True, exist_ok=True)
    (d / "job.md").write_text(f"# {role or 'Role'} @ {company or 'Company'}\n\nURL: {url}\n\n---\n\n{body}\n")
    return d
