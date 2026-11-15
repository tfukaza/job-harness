"""Playwright form filling.

Flow per job:
  1. `hj form <job> <url>`   headless: list the form's questions -> jobs/<slug>/form.json
  2. the agent writes jobs/<slug>/answers.yaml (every question, each answer with a `source`)
  3. `hj apply <job> <url>`  headed: fill answers + attach resume.pdf, then wait for the USER to submit (default)
     `hj apply ... --submit` ASSIST/YOLO MODE ONLY: also clicks Submit, if every gate below passes.

Auto-submit gates (assist and yolo modes) (all must hold, else it stops before Submit and hands over to the user):
  - main/mode.yaml has mode assist or yolo (set by the user)
  - free-text answers passed the review-answers panel (answers-review.md has `FINAL: PASS`)
  - jobs/<slug>/review.md first line is `VERDICT: PASS` (written by the review agent)
  - draft.yaml approved, resume.pdf present
  - every question on the form has an answer or `skip: true` (and nothing required is skipped)
  - no visible CAPTCHA / human-verification challenge (never solved or bypassed; the user takes over)
  - the daily cap in mode.yaml is not exceeded and this company/role is not already in the tracker
"""
import json
import time
from datetime import date
from pathlib import Path

import yaml

from .. import ROOT

PROFILE = ROOT / "main" / "profile.yaml"
MODE = ROOT / "main" / "mode.yaml"
BROWSER_PROFILE = ROOT / ".browser-profile"
SUBMIT_TEXTS = ("Submit Application", "Submit application", "Submit")


def detect_ats(url: str) -> str:
    for k in ("greenhouse", "lever", "ashby"):
        if k in url:
            return k
    return "generic"


def application_url(url: str) -> str:
    """Ashby postings have the form on a separate /application page."""
    if "ashbyhq.com" in url and not url.rstrip("/").endswith("/application"):
        return url.rstrip("/") + "/application"
    return url


# ---------- reading the form ----------

def _entries(page):
    """Question blocks. Ashby has explicit field entries; elsewhere fall back to labelled inputs."""
    loc = page.locator("[class*=application-form-field-entry]")
    if loc.count():
        return loc.all()
    return page.locator("label").all()


def _title(entry) -> str:
    t = entry.inner_text().strip().split("\n")[0].strip()
    return t.rstrip("*").strip()


def _kind(entry) -> dict:
    if entry.locator("input[type=file]").count():
        return {"type": "file"}
    if entry.locator("textarea").count():
        return {"type": "textarea"}
    if entry.locator("select").count():
        return {"type": "select", "options": entry.locator("select option").all_inner_texts()}
    btns = [b.strip() for b in entry.locator("button").all_inner_texts() if b.strip()]
    if btns and not entry.locator("input[type=text], input[type=email], input[type=tel]").count():
        return {"type": "choice", "options": btns}
    if entry.locator("input[type=radio]").count():
        return {"type": "radio", "options": [l.strip() for l in entry.locator("label").all_inner_texts()[1:]]}
    if entry.locator("input[type=checkbox]").count() == 1 and not entry.locator("input[type=text]").count():
        return {"type": "checkbox"}
    if entry.locator("[role=combobox], input[placeholder='Start typing...']").count():
        return {"type": "autocomplete"}
    return {"type": "text"}


def _required(entry) -> bool:
    if entry.locator("[required], [aria-required=true]").count():
        return True
    return "*" in entry.inner_text().split("\n")[0]


def dump_form(url: str) -> list[dict]:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        p = b.new_page()
        p.goto(application_url(url))
        p.wait_for_load_state("networkidle")
        out = []
        for e in _entries(p):
            title = _title(e)
            if title:
                out.append({"label": title, "required": _required(e), **_kind(e)})
        b.close()
    return out


# ---------- filling ----------

def _answers(job_dir: Path) -> dict:
    a = yaml.safe_load((job_dir / "answers.yaml").read_text()) or {}
    return {x["label"].strip().lower(): x for x in a.get("fields", [])}


def _fill_entry(page, entry, kind: str, ans: dict, pdf: Path) -> str:
    v = ans.get("value")
    if kind == "file":
        if ans.get("file") == "resume":
            entry.locator("input[type=file]").first.set_input_files(str(pdf))
            page.wait_for_timeout(1500)
            return "attached resume.pdf"
        return "skipped (no file)"
    if v in (None, ""):
        return "skipped (blank)"
    v = str(v)
    if kind == "textarea":
        entry.locator("textarea").first.fill(v)
    elif kind == "select":
        entry.locator("select").first.select_option(label=v)
    elif kind == "choice":
        entry.get_by_role("button", name=v, exact=True).first.click()
    elif kind == "radio":
        entry.get_by_label(v, exact=True).first.check()
    elif kind == "checkbox":
        if v.lower() in ("true", "yes", "1"):
            entry.locator("input[type=checkbox]").first.check()
    elif kind == "autocomplete":
        box = entry.locator("[role=combobox], input[placeholder='Start typing...']").first
        box.fill(v)
        page.wait_for_timeout(1200)
        opt = page.get_by_role("option").first
        if opt.count():
            opt.click()
        else:
            box.press("ArrowDown")
            box.press("Enter")
    else:
        entry.locator("input").first.fill(v)
    return "filled"


def _captcha_visible(page) -> bool:
    """A visible human-verification challenge (not the invisible score check). Never solve or bypass it."""
    for f in page.frames:
        if "recaptcha/api2/bframe" in f.url or "hcaptcha.com" in f.url and "challenge" in f.url:
            try:
                el = page.locator(f"iframe[src*='{'bframe' if 'recaptcha' in f.url else 'hcaptcha'}']").first
                if el.count() and el.is_visible():
                    return True
            except Exception:
                return True
    return False


def _yolo_gate(job_dir: Path, unanswered: list[str]) -> list[str]:
    why = []
    cfg = (yaml.safe_load(MODE.read_text()) if MODE.exists() else {}) or {}
    if cfg.get("mode") not in ("assist", "yolo"):
        why.append(f"mode is {cfg.get('mode', 'review')!r}; auto-submit needs assist or yolo (main/mode.yaml, set by the user)")
    review = job_dir / "review.md"
    if not review.exists() or not review.read_text().startswith("VERDICT: PASS"):
        why.append("review.md is missing or not 'VERDICT: PASS'")
    ar = job_dir / "answers-review.md"
    a = yaml.safe_load((job_dir / "answers.yaml").read_text()) or {}
    if any("value" in f and len(str(f["value"]).split()) > 25 for f in a.get("fields", [])):
        if not ar.exists() or "FINAL: PASS" not in ar.read_text():
            why.append("free-text answers have no 'FINAL: PASS' from the review-answers panel")
    draft = yaml.safe_load((job_dir / "draft.yaml").read_text())
    if draft.get("approved") is not True:
        why.append("draft.yaml is not approved")
    if unanswered:
        why.append(f"unanswered questions: {unanswered}")
    from .. import tracker
    rows = tracker.load()
    today = sum(1 for r in rows if r.get("date_applied", "") == date.today().isoformat())
    if today >= int(cfg.get("max_per_day", 5)):
        why.append(f"daily cap reached ({today})")
    meta = yaml.safe_load((job_dir / "answers.yaml").read_text()) or {}
    for r in rows:
        if r["company"].lower() == str(meta.get("company", "")).lower() and r["role"].lower() == str(meta.get("role", "")).lower():
            why.append("already in the tracker")
    return why


def run_apply(job_dir: Path, url: str, submit: bool = False) -> dict:
    """Fill the form. Without submit: wait until the user closes the browser. With submit: gated auto-submit."""
    from playwright.sync_api import sync_playwright

    job_dir = Path(job_dir)
    pdf = job_dir / "resume.pdf"
    if not pdf.exists():
        raise SystemExit("resume.pdf missing. Run `hj build` first.")
    if not (job_dir / "answers.yaml").exists():
        raise SystemExit("answers.yaml missing. Run `hj form` and write answers first (see the apply skill).")
    answers = _answers(job_dir)
    report = {"filled": [], "unanswered": [], "submitted": False, "stopped": ""}
    with sync_playwright() as pw:
        # no_viewport: use the real window size; a fixed viewport clips CAPTCHA frames
        ctx = pw.chromium.launch_persistent_context(str(BROWSER_PROFILE), headless=False, no_viewport=True,
                                                    args=["--start-maximized"])
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(application_url(url))
        page.wait_for_load_state("networkidle")
        for e in _entries(page):
            title = _title(e)
            if not title:
                continue
            kind = _kind(e)["type"]
            ans = answers.get(title.lower())
            if ans is None:
                report["unanswered"].append(title)
                continue
            if ans.get("skip"):
                if _required(e):
                    report["unanswered"].append(f"{title} (required but marked skip)")
                continue
            try:
                report["filled"].append(f"{title}: {_fill_entry(page, e, kind, ans, pdf)}")
            except Exception as ex:
                report["unanswered"].append(f"{title} (fill failed: {type(ex).__name__})")
        page.screenshot(path=str(job_dir / "form-filled.png"), full_page=True)

        if not submit:
            print(json.dumps(report, indent=2))
            print("\nReview the form in the browser and click Submit YOURSELF. Close the browser window when done.")
            page.wait_for_event("close", timeout=0)
            ctx.close()
            return report

        blockers = _yolo_gate(job_dir, report["unanswered"])
        if _captcha_visible(page):
            blockers.append("a CAPTCHA challenge is showing")
        if blockers:
            report["stopped"] = "; ".join(blockers)
            print(json.dumps(report, indent=2))
            print("\nAUTO-SUBMIT STOPPED before Submit. Finish in the browser yourself, then close it.")
            page.wait_for_event("close", timeout=0)
            ctx.close()
            return report

        btn = None
        for t in SUBMIT_TEXTS:
            loc = page.get_by_role("button", name=t, exact=True)
            if loc.count():
                btn = loc.first
                break
        if btn is None:
            report["stopped"] = "no Submit button found"
        else:
            btn.click()
            # A CAPTCHA after Submit is handed to the user (never solved or bypassed by code). We keep watching
            # for the confirmation page so the application is still logged once the user completes it.
            deadline, told = time.time() + 30, False
            while time.time() < deadline:
                time.sleep(1)
                try:
                    if _captcha_visible(page) and not told:
                        told = True
                        deadline = time.time() + 600
                        report["captcha"] = "handed to the user"
                        print("\nCAPTCHA showing: please solve it in the browser window. "
                              "If the form does not submit by itself after that, click Submit Application again. "
                              "Waiting up to 10 minutes...", flush=True)
                    body = page.locator("body").inner_text().lower()
                except Exception:
                    report["stopped"] = "browser was closed before a confirmation appeared"
                    break
                if any(k in body for k in ("thank you", "application submitted", "thanks for applying",
                                           "successfully submitted", "we've received", "application was successfully")):
                    report["submitted"] = True
                    break
            try:
                page.screenshot(path=str(job_dir / "form-after-submit.png"), full_page=True)
            except Exception:
                pass
            if not report["submitted"] and not report["stopped"]:
                report["stopped"] = "no confirmation seen after Submit; check the browser (errors on the form?)"
        print(json.dumps(report, indent=2))
        if report["stopped"] and "closed" not in report["stopped"]:
            print("\nLeaving the browser open for you. Close it when done.")
            page.wait_for_event("close", timeout=0)
        ctx.close()
    (job_dir / "apply-report.json").write_text(json.dumps(report, indent=2))
    return report
