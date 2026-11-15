# job-harness

Human-in-the-loop job application harness: one massive main resume -> tailored PDF per job -> upload to portal (you press Submit) -> tracker.

## Setup
```
brew install typst
uv sync
uv run playwright install chromium
cp main/main.example.md main/main.md        # then write everything you've done
cp main/profile.example.yaml main/profile.yaml
```

## Flow (⛔ = you decide)
1. `find-jobs` skill -> `search/inbox.csv`. ⛔ mark rows `interested` / `skip`.
2. `new-job` skill (<url|inbox id>) -> `jobs/<slug>/job.md`
3. `tailor-resume` skill -> `jobs/<slug>/draft.yaml` (with rationale). ⛔ edit, set `approved: true`.
4. `uv run hj build jobs/<slug>` -> `resume.pdf`. ⛔ open and check it.
5. `apply` skill (jobs/<slug>) -> browser fills the form and attaches the PDF, then pauses. ⛔ you click Submit.
6. `uv run hj track status <id> interview` as things progress.

Statuses: `applied, screen, interview, offer, rejected, withdrawn`.

Search more widely with `uv run hj search --yc` (hiring YC startups; filters in `search/criteria.yaml`).
Works with any coding agent: rules in `AGENTS.md`, skills in `.agents/skills/` (symlinked for Claude Code).
