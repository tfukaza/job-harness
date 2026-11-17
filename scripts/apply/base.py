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
    for k in ("greenhouse", "lever", "ashby", "gem.com", "workable", "recruitee", "smartrecruiters", "personio",
              "myworkdayjobs", "ycombinator"):
        if k in url:
            return k.split(".")[0].replace("myworkdayjobs", "workday")
    return "generic"


EMBED_HOSTS = ("greenhouse.io", "lever.co", "ashbyhq.com")


def _settle(page):
    try:
        page.wait_for_load_state("networkidle", timeout=8000)
    except Exception:
        page.wait_for_timeout(3000)


def _open(page, url: str):
    """Load a form page. If a company site embeds the ATS form in an iframe (common with Greenhouse), follow the
    frame's own URL so the form is the top-level page."""
    page.goto(url, wait_until="domcontentloaded")
    _settle(page)
    if page.locator("input, textarea, select").count() < 3:
        for f in page.frames[1:]:
            if any(h in f.url for h in EMBED_HOSTS) and ("job_app" in f.url or "/application" in f.url or "/apply" in f.url):
                page.goto(f.url, wait_until="domcontentloaded")
                _settle(page)
                break
    _reveal_form(page)


APPLY_TEXTS = ("Apply now", "Apply for this job", "Apply for this position", "Apply to this job", "Apply", "I'm interested")


def _visible_controls(page) -> int:
    return page.evaluate("() => [...document.querySelectorAll('input:not([type=hidden]), textarea, select')]"
                         ".filter(c => c.getClientRects().length).length")


def _reveal_form(page):
    """Some systems (Recruitee, Workable, SmartRecruiters) show the posting first and the form after an Apply click."""
    if _visible_controls(page) >= 3:
        return
    for t in APPLY_TEXTS:
        btn = page.get_by_role("button", name=t, exact=True).or_(page.get_by_role("link", name=t, exact=True))
        if btn.count():
            try:
                btn.first.click(timeout=4000)
                page.wait_for_timeout(2500)
                _settle(page)
            except Exception:
                continue
            if _visible_controls(page) >= 3:
                return


def application_url(url: str) -> str:
    """Ashby postings have the form on a separate /application page."""
    if "ashbyhq.com" in url and not url.rstrip("/").endswith("/application"):
        return url.rstrip("/") + "/application"
    if "jobs.lever.co" in url and not url.rstrip("/").endswith("/apply"):
        return url.rstrip("/") + "/apply"
    return url


# ---------- reading the form ----------

def _entries(page):
    """Question blocks. Ashby has explicit field entries; elsewhere fall back to labelled inputs."""
    for sel in ("[class*=application-form-field-entry]",   # Ashby
                "li.application-question"):                # Lever
        loc = page.locator(sel)
        if loc.count():
            # skip blocks with no form control (e.g. Lever's "apply with LinkedIn" button)
            return [e for e in loc.all() if e.locator("input, textarea, select, button").count()]
    if page.locator(".select__container, .field-wrapper").count():           # Greenhouse
        # every dropdown (incl. the voluntary self-identification survey) is a .select__container; other fields are
        # .field-wrapper blocks without a dropdown inside; the phone number sits in its own wrapper.
        loc = page.locator(".select__container, .field-wrapper:not(:has(.select__container)), .phone-input__phone, "
                           "fieldset:has(input[type=checkbox])")
        return [e for e in loc.all() if e.locator("input, textarea, select").count()]
    # any other system (Gem, Recruitee, Workable, ...): blocks.js marks each question's wrapper (same rules as fill.js)
    page.evaluate((Path(__file__).with_name("blocks.js")).read_text())
    return page.locator("[data-hj-block]").all()


def _title(entry) -> str:
    f = entry.locator("input[type=file]")
    if f.count() and f.first.get_attribute("id"):              # Greenhouse: "Attach" button; real label elsewhere
        lab = entry.page.locator(f"[id='upload-label-{f.first.get_attribute('id')}']")
        if lab.count() and lab.first.inner_text().strip():
            return lab.first.inner_text().strip().replace("✱", "").rstrip("*").strip()
    lines = [ln.replace("✱", "").strip().rstrip("*").strip() for ln in entry.inner_text().split("\n")]
    return next((ln for ln in lines if ln), "")          # first line with text (skips a lone "*" marker line)


def _kind(entry) -> dict:
    if entry.locator("input[type=file]").count():
        return {"type": "file"}
    if entry.locator("textarea").count():
        return {"type": "textarea"}
    if entry.locator("select").count():
        return {"type": "select", "options": entry.locator("select option").all_inner_texts()}
    if entry.locator("input[type=tel]").count():
        return {"type": "text"}
    if entry.locator("[role=combobox]").count() and entry.locator(".select__container, [class*=select]").count():
        return {"type": "dropdown"}       # searchable dropdown (Greenhouse react-select): type, then pick
    btns = [b.strip() for b in entry.locator("button").all_inner_texts() if b.strip()]
    if btns and not entry.locator("input[type=text], input[type=email], input[type=tel]").count():
        return {"type": "choice", "options": btns}
    if entry.locator("input[type=radio]").count():
        opts = entry.evaluate("e => [...e.querySelectorAll('input[type=radio]')].map(r => (r.labels[0] || r.parentElement).innerText.trim())")
        return {"type": "radio", "options": opts}
    if entry.locator("input[type=checkbox]").count() == 1 and not entry.locator("input[type=text]").count():
        return {"type": "checkbox"}
    if entry.locator("[role=combobox], input[placeholder='Start typing...']").count():
        return {"type": "autocomplete"}
    return {"type": "text"}


def _required(entry) -> bool:
    if entry.locator("[required], [aria-required=true]").count():
        return True
    head = " ".join(entry.inner_text().split("\n")[:2])
    return "*" in head or "✱" in head


def _dropdown_options(page, entry) -> list[str]:
    """Open a searchable dropdown, read its options, close it again (read-only)."""
    try:
        box = entry.locator("[role=combobox]").first
        box.click()
        page.wait_for_timeout(500)
        opts = [o.strip() for o in page.get_by_role("option").all_inner_texts() if o.strip()]
        box.press("Escape")
        return opts[:60]
    except Exception:
        return []


def dump_form(url: str) -> list[dict]:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        p = b.new_page()
        _open(p, application_url(url))
        out = []
        for e in _entries(p):
            title = _title(e)
            if title:
                k = _kind(e)
                if k["type"] == "dropdown":
                    k["options"] = _dropdown_options(p, e)
                out.append({"label": title, "required": _required(e), **k})
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
    elif kind == "dropdown":
        box = entry.locator("[role=combobox]").first
        box.click()
        box.fill(v.split(" +")[0])          # search text; "United States +1" -> "United States"
        page.wait_for_timeout(1000)
        opts = page.get_by_role("option")
        texts = [t.strip() for t in opts.all_inner_texts()]
        pick = next((i for i, t in enumerate(texts) if t.lower() == v.lower()), None)
        if pick is None:
            pick = next((i for i, t in enumerate(texts) if v.lower() in t.lower() or t.lower().startswith(v.lower())), None)
        if pick is None:
            raise ValueError(f"no option matching {v!r} (saw {texts[:5]})")
        opts.nth(pick).click()
    elif kind == "choice":
        entry.get_by_role("button", name=v, exact=True).first.click()
    elif kind == "radio":
        entry.get_by_label(v, exact=True).first.check()
    elif kind == "checkbox":
        if v.lower() in ("true", "yes", "1"):
            entry.locator("input[type=checkbox]").first.check()
    elif kind == "autocomplete":
        box = entry.locator("[role=combobox], input[placeholder='Start typing...']")
        box = box.first if box.count() else _text_input(entry)
        box.click()
        box.fill("")
        box.press_sequentially(v, delay=60)    # real keystrokes: lookup widgets listen to key events
        page.wait_for_timeout(1200)
        opt = page.get_by_role("option").filter(visible=True).first
        page.wait_for_timeout(1500)        # suggestions often come from a lookup API
        opt = page.get_by_role("option").filter(visible=True).first
        sugg = entry.locator("[class*=dropdown-location], [class*=suggestion], [class*=result-item], "
                             "[class*=dropdown-results] > *").filter(visible=True).first
        if opt.count():
            opt.click()
        elif sugg.count():
            sugg.click()
        else:
            box.press("ArrowDown")
            box.press("Enter")
    else:
        _text_input(entry).fill(v)
    return "filled"


def _text_input(entry):
    """The field's real text box (skips hidden helper inputs such as a phone widget's country search)."""
    for sel in ("input[type=tel]", "input[type=email]", "input[type=text]:visible", "input:visible"):
        loc = entry.locator(sel)
        if loc.count():
            return loc.first
    return entry.locator("input").first


def _readback(page, entry, kind: str, ans: dict) -> str:
    """Confirm the form now shows what we meant to put there. Returns 'ok' or a short mismatch note."""
    try:
        if kind == "file":
            return "ok" if ".pdf" in entry.inner_text() else "file name not shown after upload"
        v = str(ans.get("value", ""))
        if kind in ("text", "autocomplete"):
            got = _text_input(entry).input_value()
            return "ok" if got.strip() and (v.lower() in got.lower() or got.lower() in v.lower()) else f"shows {got!r}"
        if kind == "textarea":
            got = entry.locator("textarea").first.input_value()
            return "ok" if got.strip() == v.strip() else "text differs"
        if kind in ("dropdown", "select", "choice", "radio"):
            txt = entry.inner_text()
            if kind == "dropdown" and " +" in v:          # phone country: shown as a flag and "+1"
                name, code = v.split(" +", 1)
                return "ok" if name.lower() in txt.lower() or f"+{code}" in txt else f"selection not shown (wanted {v!r})"
            if kind == "select":
                txt = entry.locator("select").first.evaluate("e => e.options[e.selectedIndex]?.text || ''")
            return "ok" if v.lower() in txt.lower() else f"selection not shown (wanted {v!r})"
        if kind == "checkbox":
            return "ok" if entry.locator("input[type=checkbox]").first.is_checked() else "not checked"
    except Exception as ex:
        return f"could not read back ({type(ex).__name__})"
    return "ok"


def _each_entry(page, seen: set):
    """Yield each question once, re-scanning after every answer: some forms reveal follow-up questions
    (e.g. race after the Hispanic/Latino question, or 'other' text boxes)."""
    for _ in range(4):
        new = False
        for e in _entries(page):
            title = _title(e)
            if not title or title in seen:
                continue
            seen.add(title)
            new = True
            yield e
        if not new:
            return


def _upload_resume(page, job_dir: Path, pdf: Path) -> list:
    """Test stand-in for the agent's upload step: attach the PDF to every resume question, confirm it shows."""
    answers = _answers(job_dir)
    out = []
    for label, ans in answers.items():
        if ans.get("file") != "resume":
            continue
        title = ans["label"]
        target = None
        for e in _entries(page):
            if _title(e).lower() == label and e.locator("input[type=file]").count():
                target = e.locator("input[type=file]").first
                break
        if target is None:
            out.append((title, "FAIL"))
            continue
        target.set_input_files(str(pdf))
        page.wait_for_timeout(2500)          # the page may parse the resume and rebuild the field
        shown = pdf.name.lower() in page.locator("body").inner_text().lower()   # field may become a file "chip"
        out.append((title, "OK" if shown else "FAIL"))
    return out


def _agent_fill(page, job_dir: Path, rep: dict, pdf: Path, done: list):
    """Test stand-in for the agent's trusted-input steps (dropdowns, autocompletes)."""
    answers = _answers(job_dir)
    for item in [x for x in rep["needs_agent"] if x.get("kind") in ("dropdown", "text", "autocomplete")]:
        if item["label"] in done:
            continue
        for e in _entries(page):
            if _title(e).lower() == item["label"].lower():
                try:
                    # fill.js hands back plain-looking boxes that would not keep a typed value: they are lookups
                    k = "autocomplete" if item.get("kind") in ("autocomplete", "text") else _kind(e)["type"]
                    _fill_entry(page, e, k, answers[item["label"].lower()], pdf)
                    done.append(item["label"])
                except Exception as ex:
                    item["reason"] += f" (simulated agent failed: {type(ex).__name__})"
                break


def check_fill(job_dir: Path, url: str) -> dict:
    """Dry run of the hybrid fill, in the same order an agent uses in the user's browser:
    1. upload the resume (pages may parse it and overwrite fields), 2. run fill.js, 3. trusted clicks for what
    fill.js hands back (dropdowns, autocompletes), 4. run fill.js again for follow-up questions, 5. verify.js.
    Never submits."""
    from playwright.sync_api import sync_playwright
    from .plan import fill_script, verify_script
    job_dir = Path(job_dir)
    js = fill_script(job_dir)
    pdf = job_dir / "resume.pdf"
    if not pdf.exists():
        pdf = job_dir / "preview.pdf"          # dry run before approval: test the upload with the preview
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        page = b.new_page(viewport={"width": 1280, "height": 900})
        _open(page, application_url(url))
        uploads = _upload_resume(page, job_dir, pdf)
        rep = page.evaluate(js)
        done = []
        _agent_fill(page, job_dir, rep, pdf, done)
        rep2 = page.evaluate(js)                       # follow-ups revealed by earlier answers
        _agent_fill(page, job_dir, rep2, pdf, done)
        filled = set(rep["filled"]) | set(rep2["filled"])
        needs = [x for x in rep2["needs_agent"] if x["label"] not in done and x["label"] not in filled
                 and not x["reason"].startswith("upload ")]
        final = page.evaluate(verify_script(job_dir))
        page.screenshot(path=str(job_dir / "fill-check.png"), full_page=True)
        b.close()
    return {"filled": sorted(filled), "agent_done": done, "uploads": uploads, "skipped": rep["skipped"],
            "needs_agent": needs, "final": final,
            "ok": not needs and all(s == "OK" for _, s in uploads) and bool(final.get("ready"))}


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
        _open(page, application_url(url))
        for e in _each_entry(page, set()):
            title = _title(e)
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
        if detect_ats(url) == "lever":
            # Lever's invisible verification rejects automated submit clicks; the user clicks Submit there.
            blockers.append("Lever blocks automated submits: review the form and click Submit yourself")
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
                if any(k in body for k in ("error verifying your application", "verification failed",
                                           "please complete the captcha", "something went wrong")):
                    report["stopped"] = ("the site rejected the automated submit (bot/verification check). Finish in "
                                         "the browser: re-attach resume.pdf if it was cleared, then click Submit yourself")
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
