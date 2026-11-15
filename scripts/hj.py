"""hj: job harness CLI."""
from pathlib import Path

import typer

from . import tracker

app = typer.Typer(help="Human-in-the-loop job application harness", no_args_is_help=True)
track = typer.Typer(help="Application tracker", no_args_is_help=True)
app.add_typer(track, name="track")


@track.command("add")
def track_add(company: str, role: str, url: str = "", resume: str = "", portal: str = "", notes: str = "",
              status: str = "applied"):
    typer.echo(tracker.add(company, role, url, resume, portal, notes, status))


@track.command("status")
def track_status(app_id: str, status: str, note: str = ""):
    typer.echo(tracker.set_status(app_id, status, note))


@track.command("list")
def track_list(status: str = typer.Option("", help="filter by status")):
    for r in tracker.load():
        if not status or r["status"] == status:
            typer.echo(f"{r['id']:>3}  {r['status']:<10} {r['company']} - {r['role']}  ({r['updated']})")


@track.command("show")
def track_show(app_id: str):
    for r in tracker.load():
        if r["id"] == app_id:
            for k, v in r.items():
                typer.echo(f"{k}: {v}")
            return
    raise typer.Exit(1)


@app.command()
def search(yc: bool = typer.Option(False, "--yc", help="Also search hiring YC startups (discovers their job boards)"),
           refresh: bool = typer.Option(False, help="With --yc: re-probe boards instead of using the cache"),
           limit: int = typer.Option(0, help="With --yc: only probe the first N companies (testing)")):
    """Pull new postings into search/inbox.csv."""
    from . import search as s
    new = s.run(yc=yc, refresh=refresh, limit=limit or None)
    typer.echo(f"{len(new)} new postings")
    for r in new:
        typer.echo(f"  {r['id']}  {r['company']} - {r['title']} ({r['location']})")


@app.command()
def intake(target: str, company: str = "", role: str = ""):
    """Create jobs/<slug>/job.md from an inbox id or URL."""
    from .job_intake import intake as do
    typer.echo(do(target, company, role))


@app.command()
def build(job_dir: Path):
    """Render resume.pdf from an approved draft.yaml."""
    from .build import build as do
    typer.echo(do(job_dir))


@app.command()
def apply(job_dir: Path, url: str):
    """Open portal, fill, attach PDF, pause for you to submit."""
    from .apply import run_apply
    run_apply(job_dir, url)


@app.command()
def check(job_dir: Path = typer.Argument(None, help="Optional job dir: also validate its draft.yaml")):
    """Validate main/main.yaml (and a job's draft.yaml). Exit 1 on errors."""
    import yaml
    from . import ROOT
    from .check import MAIN, check_draft, check_main
    errors, warnings = check_main()
    if job_dir:
        errors += check_draft(yaml.safe_load((job_dir / "draft.yaml").read_text()) or {},
                              ROOT / "main" / "main.example.yaml" if job_dir.name == "example" else MAIN)
    for w in warnings:
        typer.echo(f"warn:  {w}")
    for e in errors:
        typer.echo(f"ERROR: {e}")
    typer.echo(f"{len(errors)} error(s), {len(warnings)} warning(s)")
    raise typer.Exit(1 if errors else 0)


if __name__ == "__main__":
    app()
