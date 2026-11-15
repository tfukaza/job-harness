"""CSV application tracker."""
import csv
from datetime import date

from . import ROOT

PATH = ROOT / "tracker" / "applications.csv"
FIELDS = ["id", "company", "role", "url", "date_applied", "status", "resume_path", "portal", "notes", "updated"]
STATUSES = ["applied", "screen", "interview", "offer", "rejected", "withdrawn"]


def load() -> list[dict]:
    if not PATH.exists():
        return []
    with PATH.open(newline="") as f:
        return list(csv.DictReader(f))


def save(rows: list[dict]) -> None:
    PATH.parent.mkdir(parents=True, exist_ok=True)
    with PATH.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def next_id(rows: list[dict]) -> str:
    return str(max([int(r["id"]) for r in rows] or [0]) + 1)


def add(company, role, url="", resume_path="", portal="", notes="", status="applied") -> dict:
    rows = load()
    today = date.today().isoformat()
    row = dict(id=next_id(rows), company=company, role=role, url=url, date_applied=today,
               status=status, resume_path=resume_path, portal=portal, notes=notes, updated=today)
    rows.append(row)
    save(rows)
    return row


def set_status(app_id: str, status: str, note: str = "") -> dict:
    if status not in STATUSES:
        raise ValueError(f"status must be one of {STATUSES}")
    rows = load()
    for r in rows:
        if r["id"] == app_id:
            r["status"] = status
            r["updated"] = date.today().isoformat()
            if note:
                r["notes"] = (r["notes"] + "; " if r["notes"] else "") + note
            save(rows)
            return r
    raise KeyError(f"no application with id {app_id}")


def urls() -> set[str]:
    return {r["url"] for r in load() if r["url"]}
