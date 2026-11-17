"""Fill plan: everything an agent needs to fill an application in the USER'S OWN browser with whatever browser or
computer-use tool it has (Claude in Chrome, Claude/Codex computer use, cmux-cua, chrome-devtools MCP, ...).

The harness stays tool-agnostic: it decides WHAT goes into the form (answers.yaml, resume.pdf) and WHETHER the agent
may click Submit (the same gates as `hj apply --submit`). The agent's own tool decides HOW to click and type.
"""
import json
from pathlib import Path

import yaml

from .base import MODE, application_url, detect_ats, _yolo_gate


def build(job_dir: Path, url: str) -> dict:
    job_dir = Path(job_dir).resolve()
    form = json.loads((job_dir / "form.json").read_text()) if (job_dir / "form.json").exists() else []
    a = yaml.safe_load((job_dir / "answers.yaml").read_text()) or {}
    answers = {f["label"].strip().lower(): f for f in a.get("fields", [])}
    steps, unanswered = [], []
    for q in form:
        ans = answers.get(q["label"].strip().lower())
        if ans is None:
            unanswered.append(q["label"])
            continue
        if ans.get("skip"):
            if q.get("required"):
                unanswered.append(f"{q['label']} (required but marked skip)")
            continue
        step = {"label": q["label"], "type": q["type"], "required": q.get("required", False)}
        if ans.get("file") == "resume":
            step["upload"] = str(job_dir / "resume.pdf")
        else:
            step["value"] = str(ans.get("value", ""))
        if q.get("options"):
            step["options"] = q["options"]
        steps.append(step)
    cfg = (yaml.safe_load(MODE.read_text()) if MODE.exists() else {}) or {}
    blockers = _yolo_gate(job_dir, unanswered)
    return {
        "company": a.get("company", ""), "role": a.get("role", ""),
        "url": application_url(url), "ats": detect_ats(url),
        "mode": cfg.get("mode", "review"),
        "may_click_submit": not blockers,
        "submit_blockers": blockers,
        "resume": str(job_dir / "resume.pdf"),
        "steps": steps,
    }


def write(job_dir: Path, url: str) -> Path:
    p = build(job_dir, url)
    job_dir = Path(job_dir)
    (job_dir / "fill-plan.json").write_text(json.dumps(p, indent=2))
    lines = [f"# Fill plan: {p['company']} - {p['role']}", "",
             f"Open in the user's own browser: {p['url']}  (ATS: {p['ats']}, mode: {p['mode']})", "",
             "| # | Question | Type | Do |", "|---|---|---|---|"]
    for i, s in enumerate(p["steps"], 1):
        do = f"upload file `{s['upload']}`" if "upload" in s else f"`{s['value']}`"
        if s.get("options"):
            do += f" (options: {', '.join(s['options'])})"
        lines.append(f"| {i} | {s['label']}{' *' if s['required'] else ''} | {s['type']} | {do} |")
    lines += ["", "Leave every other field as is. Do not use 'Apply with LinkedIn/Google' autofill unless the user asks;",
              "it can overwrite these answers.", ""]
    if p["may_click_submit"]:
        lines.append("**Submit:** allowed (all gates pass). Click Submit once, then wait for the confirmation page.")
    else:
        lines.append("**Submit: NOT allowed.** Stop after filling and hand over to the user. Reasons:")
        lines += [f"- {b}" for b in p["submit_blockers"]]
    (job_dir / "fill-plan.md").write_text("\n".join(lines) + "\n")
    return job_dir / "fill-plan.md"


TEMPLATE = Path(__file__).with_name("fill.js.tpl")


def fill_script(job_dir: Path) -> str:
    """fill.js for this job: the deterministic part of filling (text, dropdowns, yes/no, free text already written in
    answers.yaml). Uploads, LinkedIn/Google sync, CAPTCHAs and Submit stay with the agent."""
    a = yaml.safe_load((Path(job_dir) / "answers.yaml").read_text()) or {}
    rows = []
    for f in a.get("fields", []):
        r = {"label": f["label"]}
        if f.get("skip"):
            r["skip"] = True
        elif f.get("file"):
            r["file"] = str((Path(job_dir) / "resume.pdf").resolve()) if f["file"] == "resume" else f["file"]
        else:
            r["value"] = str(f.get("value", ""))
        rows.append(r)
    tpl = TEMPLATE.read_text().replace("__BLOCKS__", (TEMPLATE.with_name("blocks.js")).read_text().strip().rstrip(";"))\
        .replace("__ANSWERS__", json.dumps(rows, ensure_ascii=False))
    js = tpl.replace("__MODE__", "fill")
    (Path(job_dir) / "fill.js").write_text(js)
    (Path(job_dir) / "verify.js").write_text(tpl.replace("__MODE__", "verify"))   # final check before Submit
    return js


def verify_script(job_dir: Path) -> str:
    fill_script(job_dir)
    return (Path(job_dir) / "verify.js").read_text()
