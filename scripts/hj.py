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
def batch(n: int = typer.Option(5, "-n", help="How many candidates to show")):
    """Show the top-N undecided postings (ranked with learned preferences). WIP ranking."""
    from .feedback import batch as do
    rows = do(n)
    typer.echo("(WIP ranking: crude heuristic. level comes from `hj assess`; see search/criteria.yaml)")
    if not rows:
        typer.echo("Nothing undecided. Run `hj search` (or `hj search --yc`) for more.")
    for r in rows:
        typer.echo(f"{r['id']}  [{r['score']}] ({'yrs ' + r['years_req'] if r.get('years_req') else (r.get('level') or 'unassessed')})  {r['company']} - {r['title']} ({r['location']})")
        if r.get("level_note"):
            typer.echo(f"          level: {r['level_note']}")
        if r.get("fit_note"):
            typer.echo(f"          {r['fit_note']}")
        typer.echo(f"          {r['url']}")


@app.command()
def feedback(job_id: str, verdict: str = typer.Argument(..., help="like | dislike"),
             reason: str = typer.Option("", "--reason", "-r", help="Why (kept in the log; read by the agent)")):
    """Record your verdict on an inbox posting; updates inbox + learned preferences."""
    from .feedback import record
    try:
        row = record(job_id, verdict, reason)
    except (KeyError, ValueError) as e:
        typer.echo(f"ERROR: {e}")
        raise typer.Exit(1)
    typer.echo(f"{verdict}: {row['company']} - {row['title']} -> {row['decision']}")


@app.command()
def assess(ids: list[str] = typer.Argument(None, help="Inbox ids; omit with --pending"),
           pending: bool = typer.Option(False, "--pending", help="Assess undecided rows not yet assessed"),
           n: int = typer.Option(15, "-n", help="With --pending: how many"),
           model: str = typer.Option("", help="Override the model (default: criteria `assess_model` or claude-haiku-5-5)")):
    """Read postings with a cheap LLM; record required years, real seniority and pay. Needs Anthropic credentials."""
    import yaml
    from .assess import DEFAULT_MODEL, Assessment, run as do
    from .feedback import blocked, load_prefs, score
    from .search import CRIT, load_inbox
    crit = yaml.safe_load(CRIT.read_text()) or {}
    use = model or crit.get("assess_model") or DEFAULT_MODEL
    ids = list(ids or [])
    if pending:
        prefs = load_prefs()
        rows = [r for r in load_inbox() if r["decision"] == "new" and not r.get("level") and not r.get("years_req")
                and not blocked(r["company"], r["title"], prefs)]
        rows.sort(key=lambda r: -score(r, prefs))
        ids += [r["id"] for r in rows[:n]]
    if not ids:
        typer.echo("Nothing to assess.")
        return
    bad = 0
    for row, a in do(ids, use):
        if isinstance(a, Assessment):
            typer.echo(f"{row['id']}  {row['company']} - {row['title']}\n          {row['level']}, years_req={row['years_req'] or '-'}"
                       f"  ({row['level_note']})")
        else:
            bad += 1
            typer.echo(f"{row['id']}  FAILED {row['company']} - {row['title']}: {a}")
    if bad:
        typer.echo(f"{bad} failed. If this is an auth error, set ANTHROPIC_API_KEY or run `ant auth login`.")
        raise typer.Exit(1)


@app.command()
def level(job_id: str, years: str = typer.Argument("", help="Minimum years the posting asks for; '' if not stated"),
          note: str = typer.Option("", "--note", "-n", help="e.g. 'asks 5+ yrs, owns services end to end'")):
    """Record a posting's required years of experience (agent-checked). Out-of-range rows leave `hj batch`."""
    from .feedback import set_level
    try:
        r = set_level(job_id, years, note)
    except (KeyError, ValueError) as e:
        typer.echo(f"ERROR: {e}")
        raise typer.Exit(1)
    typer.echo(f"{r['company']} - {r['title']}: years_req={r['years_req'] or '?'}")


@app.command()
def prefs():
    """Show learned preferences and recent feedback."""
    import yaml
    from .feedback import history, load_prefs
    p = load_prefs()
    typer.echo(yaml.safe_dump(p, sort_keys=False).rstrip())
    h = history()[-10:]
    typer.echo(f"\nlast {len(h)} verdicts:")
    for r in h:
        typer.echo(f"  {r['verdict']:<7} {r['company']} - {r['title']}  {('| ' + r['reason']) if r['reason'] else ''}")


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
