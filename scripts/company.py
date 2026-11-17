"""Company research notes + total-compensation (TC) estimates.

Research is done by the agent (web search) and recorded here; code only stores it, does the arithmetic and prints it.
Everything in here is an ESTIMATE from public information, never an employer figure, and the card always says so.

Files (gitignored): search/company-research/<slug>.yaml  (one per company: what it does, stage, valuation, sources)
Per-posting estimate lives in search/inbox.csv columns tc_low, tc_high, tc_conf, tc_basis.
"""
import re
from datetime import date

import yaml

from . import ROOT
from .search import load_inbox, save_inbox

DIR = ROOT / "search" / "company-research"
CONF = ("low", "medium", "high")


def slug(name: str) -> str:
    name = re.sub(r"\s*\(.*?\)\s*$", "", name)      # "AgentMail (YC Summer 2025)" -> "AgentMail"
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def load(name: str) -> dict | None:
    p = DIR / f"{slug(name)}.yaml"
    return yaml.safe_load(p.read_text()) if p.exists() else None


def save(data: dict) -> dict:
    """data needs company, about (1-3 sentences), stage, sources (list). Optional: valuation, headcount, notes."""
    for k in ("company", "about", "stage", "sources"):
        if not data.get(k):
            raise ValueError(f"missing {k}")
    if not isinstance(data["sources"], list):
        raise ValueError("sources must be a list of URLs")
    if len(re.findall(r"[.!?](?:\s|$)", data["about"].strip())) > 3:
        raise ValueError("about: keep it to about two sentences")
    data = {**data, "researched": date.today().isoformat()}
    DIR.mkdir(parents=True, exist_ok=True)
    (DIR / f"{slug(data['company'])}.yaml").write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
    return data


def missing(rows: list[dict]) -> list[str]:
    """Company names among `rows` that have no research file yet (order kept, no duplicates)."""
    out = []
    for r in rows:
        if r["company"] not in out and load(r["company"]) is None:
            out.append(r["company"])
    return out


def k(n: float) -> str:
    return f"${n / 1000:,.0f}K" if n < 1_000_000 else f"${n / 1_000_000:,.1f}M"


def estimate_tc(job_id: str, base_low: float, base_high: float, equity_low: float, equity_high: float,
                confidence: str, basis: str, bonus: float = 0) -> dict:
    """Record an annual TC estimate for one posting: base + annualized equity (+ bonus). All USD per year."""
    if confidence not in CONF:
        raise ValueError(f"confidence must be one of {CONF}")
    if not basis.strip():
        raise ValueError("basis: say where base and equity numbers come from")
    if base_low > base_high or equity_low > equity_high:
        raise ValueError("low must be <= high")
    inbox = load_inbox()
    row = next((r for r in inbox if r["id"] == job_id), None)
    if not row:
        raise KeyError(f"no inbox row {job_id}")
    row["tc_low"] = str(round(base_low + equity_low + bonus))
    row["tc_high"] = str(round(base_high + equity_high + bonus))
    row["tc_conf"] = confidence
    row["tc_basis"] = f"base {k(base_low)}-{k(base_high)} + equity ~{k(equity_low)}-{k(equity_high)}/yr" \
                      + (f" + bonus ~{k(bonus)}" if bonus else "") + f"; {basis.strip()}"
    save_inbox(inbox)
    return row


def tc_line(row: dict) -> str:
    if not row.get("tc_low"):
        return "(not estimated yet)"
    return (f"~{k(float(row['tc_low']))}-{k(float(row['tc_high']))}/yr  ** ESTIMATE, not from the employer "
            f"(confidence: {row.get('tc_conf') or '?'}) **\n"
            f"            how: {row.get('tc_basis', '')}")
