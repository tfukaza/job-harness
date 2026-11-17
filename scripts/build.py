"""draft.yaml -> resume.pdf (+ .png) via Typst, auto-fitted to exactly one full page.

Layout is code, not model judgment: the template has fixed styles and three knobs (size, lead, gap). `fit` tries
presets from loosest to tightest, keeps the loosest that fits on one page, and reports how full the page is plus
plain-code layout warnings (long bullets, short last lines, keyword overuse). The draft author only changes content.

`build(..., preview=True)` works on unapproved drafts (writes preview.pdf/png with a DRAFT footer);
the final build refuses unless the user set `approved: true`.
"""
import json
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from . import ROOT
from .check import MAIN, check_draft

REQUIRED = ["header", "experience", "education", "skills"]
TEMPLATE = ROOT / "templates" / "resume.typ"

# Loosest first. Font size is fixed at 10pt (every style): page fill comes from content, not bigger text or airy spacing.
# Only small spacing adjustments are allowed (lead and gap in em, see templates/resume.typ).
PRESETS = [
    {"size": 10.0, "lead": 0.70, "gap": 1.05},
    {"size": 10.0, "lead": 0.66, "gap": 0.95},
    {"size": 10.0, "lead": 0.62, "gap": 0.85},
]
PAGE_H, MARGIN_Y, MARGIN_X, PAGE_W = 792.0, 36.0, 43.2, 612.0   # us-letter, 0.5in / 0.6in margins (template)
USABLE_H = PAGE_H - 2 * MARGIN_Y
CAP = 0.714            # cap height of the body font as a fraction of size (line pitch = size * (CAP + lead))
FILL_MIN = 0.95
MAX_KEYWORDS, MAX_KW_PER_BULLET = 15, 2


@dataclass
class Fit:
    preset: dict
    pages: int
    fill: float                    # fraction of the usable height used on the last page
    verdict: str                   # OK | UNDER | OVER
    advice: str
    warnings: list = field(default_factory=list)


def _pt(s: str) -> float:
    return float(s.removesuffix("pt"))


def _style() -> str:
    """The user's personal look (main/resume-style.yaml) if present, else the tracked default."""
    mine = ROOT / "main" / "resume-style.yaml"
    return "/main/resume-style.yaml" if mine.exists() else "/templates/styles/traditional.yaml"


def _font_paths() -> list[str]:
    """Extra font folders from the style file (`font_paths`, relative to the repo or absolute)."""
    user = yaml.safe_load((ROOT / _style().lstrip("/")).read_text()) or {}
    base = ROOT / "templates" / "styles" / f"{user.get('base', 'traditional')}.yaml"
    st = {**(yaml.safe_load(base.read_text()) or {}), **user}
    out = []
    for f in st.get("font_paths") or []:
        d = (ROOT / f).resolve() if not Path(f).is_absolute() else Path(f)
        if d.is_dir():
            out += ["--font-path", str(d)]
    return out


def _inputs(rel: str, preset: dict, preview: bool) -> list[str]:
    args = [*_font_paths(), "--input", f"data={rel}", "--input", f"style={_style()}"]
    for k, v in preset.items():
        args += ["--input", f"{k}={v}"]
    return args + ["--input", f"preview={'1' if preview else '0'}"]


def _eval(rel: str, preset: dict, expr: str):
    r = subprocess.run(["typst", "eval", expr, "--in", str(TEMPLATE), "--root", str(ROOT), *_inputs(rel, preset, False)],
                       capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"typst failed:\n{r.stderr.strip()}")
    return json.loads(r.stdout)


def _rel(draft_path: Path) -> str:
    # leading "/" makes Typst resolve the data path from --root, not from the template folder
    return "/" + str(draft_path.resolve().relative_to(ROOT))


def _line_pitch(p: dict) -> float:
    return p["size"] * (CAP + p["lead"])


def _warnings(draft: dict, p: dict, marks: list) -> list[str]:
    out = []
    avail = PAGE_W - 2 * MARGIN_X
    starts = {}
    for m in marks:
        if m["kind"] == "s":
            starts[m["id"]] = m
            continue
        s = starts.get(m["id"])
        if not s:
            continue
        width = avail - (_pt(s["pos"]["x"]) - MARGIN_X)
        if m["id"] == "summary":
            # plain paragraph: its markers sit on block edges, so estimate lines from the text width instead
            lines = max(1, -(-int(_pt(s["w"]) * 1.04) // int(width)))
        else:
            dy = _pt(m["pos"]["y"]) - _pt(s["pos"]["y"])
            lines = 1 + max(0, round((dy - CAP * p["size"]) / _line_pitch(p)))
        last = _pt(s["w"]) - (lines - 1) * width
        if lines > (3 if m["id"] == "summary" else 2):
            out.append(f"{m['id']}: {lines} lines; keep {'the summary to 2-3' if m['id'] == 'summary' else 'bullets to 1-2'} lines")
        if lines > 1 and last < 0.18 * width:
            out.append(f"{m['id']}: last line is only a word or two; tighten it to one line or lengthen it "
                       "with true detail from main.yaml")
    kws = draft.get("keywords") or []
    if len(kws) > MAX_KEYWORDS:
        out.append(f"{len(kws)} keywords; bold at most {MAX_KEYWORDS} so they still stand out")
    texts = [b.get("text", "") for sect in ("experience", "projects") for e in draft.get(sect) or []
             for b in e.get("bullets", [])]
    for k in kws:
        if not any(k in t for t in texts + [draft.get("summary") or ""]):
            out.append(f"keyword {k!r} appears nowhere (match is exact and case-sensitive)")
    for t in texts:
        n = sum(1 for k in kws if k in t)
        if n > MAX_KW_PER_BULLET:
            out.append(f"{n} keywords bolded in one bullet ({t[:40]!r}...); keep it to {MAX_KW_PER_BULLET}")
    if len({t.rstrip().endswith(".") for t in texts if t.strip()}) > 1:
        out.append("some bullets end with a period and some do not; pick one (house style: no period)")
    for sect in ("experience", "projects"):
        for e in draft.get(sect) or []:
            if not e.get("bullets"):
                out.append(f"{e.get('company') or e.get('name')}: no bullets")
    return out


def fit(draft_path: Path, draft: dict) -> Fit:
    """Pick the loosest preset that fits on one page and say whether the content under- or over-fills it."""
    rel = _rel(draft_path)
    for p in PRESETS:
        end = _eval(rel, p, "query(<end>).map(it => it.value)")[0]
        page, fill = end["page"], (_pt(end["y"]) - MARGIN_Y) / USABLE_H
        if page == 1:
            break
    marks = _eval(rel, p, "query(<bl>).map(it => it.value)")
    warns = _warnings(draft, p, marks)
    lines = lambda frac: max(1, round(frac * USABLE_H / _line_pitch(p)))
    if page > 1:
        return Fit(p, page, fill, "OVER",
                   f"Does not fit on one page even at the tightest spacing: cut about {lines(page - 2 + fill) + 1} "
                   "line(s). Drop the least relevant bullet first; never change fonts or spacing.", warns)
    if fill < FILL_MIN and p is PRESETS[0]:
        return Fit(p, page, fill, "UNDER",
                   f"Page is {fill:.0%} full at the roomiest spacing: add about {lines(0.97 - fill)} line(s) of "
                   "relevant content from main/main.yaml (next-best bullets, or a project).", warns)
    return Fit(p, page, fill, "OK", f"One page, {fill:.0%} full.", warns)


def _validate(job_dir: Path, draft: dict):
    missing = [k for k in REQUIRED if k not in draft]
    if missing:
        raise SystemExit(f"draft.yaml missing keys: {missing}")
    for sect in ("experience", "projects"):
        for e in draft.get(sect) or []:
            for b in e.get("bullets", []):
                if not b.get("source"):
                    raise SystemExit(f"bullet without main source: {b.get('text', '')[:60]!r}")
    # The tracked sample draft is validated against the tracked sample main resume.
    main_path = ROOT / "main" / "main.example.yaml" if job_dir.name == "example" else MAIN
    problems = check_draft(draft, main_path)
    if problems:
        raise SystemExit("draft.yaml problems:\n  " + "\n  ".join(problems))


def build(job_dir: Path, preview: bool = False) -> tuple[Path, Fit]:
    job_dir = Path(job_dir)
    draft_path = job_dir / "draft.yaml"
    draft = yaml.safe_load(draft_path.read_text())
    if not preview and draft.get("approved") is not True:
        raise SystemExit(f"{draft_path} is not approved. Review it and set `approved: true` "
                         "(or run `hj build --preview` to look at it first).")
    _validate(job_dir, draft)
    if not shutil.which("typst"):
        raise SystemExit("typst not found. Install with `brew install typst`.")
    f = fit(draft_path, draft)
    name = "preview" if preview else "resume"
    for old in job_dir.glob(f"{name}-*.png"):   # drop stale pages from earlier renders
        old.unlink()
    base = ["typst", "compile", "--root", str(ROOT), *_inputs(_rel(draft_path), f.preset, preview), str(TEMPLATE)]
    for target in ([str(job_dir / f"{name}.pdf")], ["--ppi", "110", str(job_dir / f"{name}-{{p}}.png")]):
        r = subprocess.run(base + target, capture_output=True, text=True)
        if r.returncode:
            raise SystemExit(f"typst failed:\n{r.stderr.strip()}")
    return job_dir / f"{name}.pdf", f
