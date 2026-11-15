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
    from .feedback import format_card
    for r in rows:
        typer.echo("\n" + format_card(r))


@app.command()
def show(job_id: str):
    """Show one inbox posting in the standard card format."""
    from .feedback import format_card, load_prefs, score
    from .search import load_inbox
    r = next((x for x in load_inbox() if x["id"] == job_id), None)
    if not r:
        typer.echo(f"ERROR: no inbox row {job_id}")
        raise typer.Exit(1)
    typer.echo(format_card(dict(r, score=score(r, load_prefs()))))


@app.command()
def rate(job_id: str,
         score: str = typer.Option("", "--score", "-s", help="Fit 1-5"),
         why: str = typer.Option("", "--why", "-w", help="Why it fits THIS user (cite their experience) + one gap"),
         summary: str = typer.Option("", "--summary", help="1-2 plain sentences: what the company/role does"),
         comp: str = typer.Option("", "--comp", help="Pay as stated, e.g. '$200K-$250K + equity'")):
    """Record the agent's judgment for a posting (fit score, why-it-fits, summary, comp)."""
    from .feedback import rate as do
    try:
        r = do(job_id, score, why, summary, comp)
    except (KeyError, ValueError) as e:
        typer.echo(f"ERROR: {e}")
        raise typer.Exit(1)
    typer.echo(f"rated {r['company']} - {r['title']}")


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


assess = typer.Typer(help="Read postings for required years / real seniority / pay (see the assess-postings skill)",
                     no_args_is_help=True)
app.add_typer(assess, name="assess")


@assess.command("prep")
def assess_prep(ids: list[str] = typer.Argument(None, help="Inbox ids; omit with --pending"),
                pending: bool = typer.Option(False, "--pending", help="Undecided rows not yet assessed"),
                n: int = typer.Option(15, "-n", help="With --pending: how many")):
    """Fetch posting text to search/postings/<id>.txt for a (cheap-model) subagent to read."""
    from .assess import prep
    from .feedback import blocked, load_prefs, score
    from .search import load_inbox
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
    for row, err in prep(ids):
        typer.echo(f"{'FAILED ' if err else 'ok     '}{row['id']}  {row['company']} - {row['title']}"
                   + (f"  ({err})" if err else f"  -> search/postings/{row['id']}.txt"))


@assess.command("save")
def assess_save():
    """Read subagent JSON (an object or array with an `id` each) from stdin, validate it, write it to the inbox."""
    import sys
    from .assess import save
    try:
        results = save(sys.stdin.read())
    except ValueError as e:  # bad JSON
        typer.echo(f"ERROR: not valid JSON: {e}")
        raise typer.Exit(1)
    bad = 0
    for i, err in results:
        bad += bool(err)
        typer.echo(f"{'REJECTED ' if err else 'saved    '}{i}{'  ' + err if err else ''}")
    raise typer.Exit(1 if bad else 0)


@assess.command("schema")
def assess_schema():
    """Print the JSON the subagent must return (for the skill prompt)."""
    import json
    from .assess import AssessmentIn
    typer.echo(json.dumps(AssessmentIn.model_json_schema(), indent=2))


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
