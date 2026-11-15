"""draft.yaml -> resume.pdf via Typst. Refuses unapproved drafts."""
import shutil
import subprocess
from pathlib import Path

import yaml

from . import ROOT

REQUIRED = ["header", "experience", "education", "skills"]


def build(job_dir: Path, template: str = "resume.typ") -> Path:
    job_dir = Path(job_dir)
    draft_path = job_dir / "draft.yaml"
    draft = yaml.safe_load(draft_path.read_text())
    if draft.get("approved") is not True:
        raise SystemExit(f"{draft_path} is not approved. Review it and set `approved: true`.")
    missing = [k for k in REQUIRED if k not in draft]
    if missing:
        raise SystemExit(f"draft.yaml missing keys: {missing}")
    for e in draft["experience"]:
        for b in e.get("bullets", []):
            if not b.get("source"):
                raise SystemExit(f"bullet without main source: {b.get('text', '')[:60]!r}")
    if not shutil.which("typst"):
        raise SystemExit("typst not found. Install with `brew install typst`.")
    out = job_dir / "resume.pdf"
    subprocess.run(["typst", "compile", "--root", str(ROOT), "--input", f"data={draft_path.resolve().relative_to(ROOT)}",
                    str(ROOT / "templates" / template), str(out)], check=True)
    return out
