"""Playwright form-filling. Fills + attaches the PDF, then PAUSES. Never submits."""
import re
from pathlib import Path

import yaml

from .. import ROOT

PROFILE = ROOT / "main" / "profile.yaml"
BROWSER_PROFILE = ROOT / ".browser-profile"


def detect_ats(url: str) -> str:
    if "greenhouse.io" in url:
        return "greenhouse"
    if "lever.co" in url:
        return "lever"
    if "ashbyhq.com" in url:
        return "ashby"
    return "generic"


def fill_by_label(page, label_regex: str, value: str) -> bool:
    if not value:
        return False
    loc = page.get_by_label(re.compile(label_regex, re.I)).first
    try:
        if loc.count() and loc.is_visible():
            loc.fill(str(value))
            return True
    except Exception:
        pass
    return False


def fill_common(page, p: dict) -> list[str]:
    filled = []
    fields = [
        ("first name", p.get("first_name")), ("last name", p.get("last_name")),
        (r"^(full )?name", p.get("name")), ("email", p.get("email")), ("phone", p.get("phone")),
        ("linkedin", p.get("links", {}).get("linkedin")), ("github", p.get("links", {}).get("github")),
        ("website|portfolio", p.get("links", {}).get("website")), ("location|city", p.get("location")),
    ]
    for label, val in fields:
        if fill_by_label(page, label, val):
            filled.append(label)
    return filled


def attach_resume(page, pdf: Path) -> bool:
    inputs = page.locator("input[type=file]")
    if inputs.count() == 0:
        return False
    inputs.first.set_input_files(str(pdf))
    return True


def run_apply(job_dir: Path, url: str) -> None:
    from playwright.sync_api import sync_playwright

    job_dir = Path(job_dir)
    pdf = job_dir / "resume.pdf"
    if not pdf.exists():
        raise SystemExit("resume.pdf missing. Run `hj build` first.")
    profile = yaml.safe_load(PROFILE.read_text())
    ats = detect_ats(url)
    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(str(BROWSER_PROFILE), headless=False)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(url)
        page.wait_for_load_state("domcontentloaded")
        filled = fill_common(page, profile)  # ATS-specific adapters can extend this per `ats`
        attached = attach_resume(page, pdf)
        print(f"ATS: {ats}\nFilled: {filled}\nResume attached: {attached}")
        print("\nReview the form in the browser, answer remaining questions, and click Submit YOURSELF.")
        input("Press Enter here when done (this closes the browser)... ")
        ctx.close()
