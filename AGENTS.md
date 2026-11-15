# Job Harness: instructions for any coding agent

This repo turns the user's `main/main.yaml` into tailored resumes and helps them apply.
**Human-in-the-loop is non-negotiable.** The user decides at every ⛔ gate below.

## Hard rules
1. **Never click Submit / Apply / Send** on any portal. Adapters stop before submission; the user submits.
2. **Never invent facts.** Every bullet in a `draft.yaml` must trace to `main/main.yaml`. You may reword for clarity, relevance and concision; you may not add employers, titles, dates, skills, tools, or metrics that are not in the main resume.
3. **Always go through the draft.** Write `jobs/<slug>/draft.yaml` with `approved: false` and a `rationale` for every pick and notable omission. Only the user sets `approved: true`. `hj build` refuses otherwise.
4. Do not mark anything `interested` in `search/inbox.csv` or change tracker status to `applied` without the user saying so.
5. Personal data (`main/`, `jobs/`, `tracker/`, `search/inbox.csv`, `search/feedback.csv`, `search/preferences.yaml`, `search/postings/`) is gitignored. Never commit or send it elsewhere.
6. **Never write regexes to interpret job-posting text** (requirements, level, pay). Use the `assess-postings` skill: a cheap-model subagent reads it.

## Set up (when the user says "set up the harness")
Ask before installing anything. Run these yourself where you can:
1. `uv sync`. Needs [uv](https://docs.astral.sh/uv/) and Python 3.10+.
2. Check `typst` is on PATH (for `hj build`; `brew install typst` or typst.app) and Chromium is installed
   (`uv run playwright install chromium`, for `hj apply`). Offer to install what is missing.
3. Copy the templates to the user's private files (all gitignored):
   `main/main.example.yaml` -> `main/main.yaml`, `main/profile.example.yaml` -> `main/profile.yaml`,
   `search/criteria.example.yaml` -> `search/criteria.yaml`, `search/companies.example.yaml` -> `search/companies.yaml`.
4. Resume: ask the user for their resume(s) and build `main/main.yaml` from them: **everything, every bullet**, each with
   a stable `id` and `tags` (schema in `main.example.yaml`; wording per the `resume-style` skill). Run `uv run hj check`
   and fix what it reports. Do not invent anything; put doubts in a bullet's `note:` and ask.
5. Run the `setup-profile` skill (the questions portals keep asking) to write `main/profile.yaml`.
6. Edit `search/criteria.yaml` with the user: `titles`, `locations`, `years_required` (min/max years the user is
   willing to apply for) and `have_years`.

## Workflow (⛔ = the user decides)
1. `find-jobs` skill: pulls postings, assesses what each really requires, shows 3-5 candidate cards.
   ⛔ The user says like or dislike **and why** for each; you record it (`hj feedback`).
2. `new-job` skill (id or url): `jobs/<slug>/job.md`.
3. `tailor-resume` skill: `jobs/<slug>/draft.yaml` with rationale. ⛔ User edits and sets `approved: true`.
4. `uv run hj build jobs/<slug>`: `resume.pdf`. ⛔ User opens and checks it.
5. `apply` skill: browser fills the form and attaches the PDF, then pauses. ⛔ The user clicks Submit.
6. `track` skill / `hj track status <id> interview` as things progress.
   Statuses: `applied, screen, interview, offer, rejected, withdrawn`.

### The job-hunt loop (feedback improves the next round)
- Each round: `hj prefs` (what was learned) -> `hj search [--yc]` -> `assess-postings` on ~15 candidates -> `hj rate`
  your fit judgment -> show 3-5 cards (`hj batch`) -> user feedback -> `hj feedback` -> distill reasons into
  `search/preferences.yaml` notes/blocks (confirm blocks with the user) -> offer another round.
- **Ranking is WIP.** Score = your `fit_score` (1-5) + learned weights on title words, company and city (±0.5 per vote,
  capped ±3). Treat scores as hints; say so when a ranking looks off.
- **Level is judged by years required, not titles** (titles inflate or deflate per company). `assess-postings` records
  `years_req` (only real requirements), true seniority, pay and a summary; `hj batch` then hides postings outside
  `years_required` in `criteria.yaml`. Postings stating no years, spanning levels, or welcoming all levels stay visible.
  Compare against the user's `have_years`, never their job title.
- **Show every job as the standard card** (`hj batch` / `hj show <id>`; do not drop or reorder fields): company, role,
  comp, location, level, about, why it fits you, link. "Why you" cites the user's real experience from `main.yaml`
  and names one gap.

## Commands (`uv run hj ...`)
| Command | Purpose |
|---|---|
| `search [--yc]` | Pull postings (Greenhouse/Lever/Ashby APIs; `--yc` adds hiring YC startups) into `search/inbox.csv`; filters from `criteria.yaml`; blocked companies/titles dropped |
| `assess prep\|save\|schema` | Plumbing for `assess-postings`: `prep` fetches posting text to `search/postings/<id>.txt`; `save` validates subagent JSON from stdin and records it; `schema` prints the JSON shape |
| `batch [-n 5]` / `show <id>` | Top undecided postings (level-filtered, ranked) as standard cards |
| `rate <id> -s 1-5 -w "why it fits" [--summary --comp]` | Record your judgment for a posting |
| `feedback <id> like\|dislike -r "why"` | Record the user's verdict; sets inbox decision; updates `search/preferences.yaml` |
| `level <id> <years> -n "why"` | Manually set a posting's required years |
| `prefs` | Show learned weights, blocks, notes, recent verdicts |
| `intake <url\|id>` | Create `jobs/<slug>/job.md` |
| `check [job-dir]` | Validate `main/main.yaml` (duplicate ids, empty text, placeholders like TODO/XX%, open `note:`s) and a draft's source ids |
| `build <job-dir>` | `draft.yaml` -> `resume.pdf` via Typst; refuses unapproved drafts, unknown ids, placeholders |
| `apply <job-dir> <url>` | Open the portal, fill, attach the PDF, **pause** for the user to submit |
| `track add\|status\|list\|show` | `tracker/applications.csv` |

## Skills (agent-agnostic playbooks)
Plain-markdown playbooks in `.agents/skills/<name>/SKILL.md`: `setup-profile`, `find-jobs`, `assess-postings`,
`new-job`, `tailor-resume`, `resume-style`, `apply`, `track`. If your agent has no native skill loader, read the
matching file and follow it as written. (`.claude/skills` is a symlink to `.agents/skills`.) Deterministic work is in
the CLI; you do only judgment steps (scoring fit, tailoring, wording, launching cheap subagents).

## Layout
```
main/            main.yaml, profile.yaml (user's, ignored) + *.example.yaml templates
search/          criteria.yaml, companies.yaml (user's); inbox.csv, feedback.csv, preferences.yaml, postings/ (generated, ignored)
jobs/<slug>/     job.md, draft.yaml, resume.pdf per application (ignored; jobs/example is a tracked sample)
tracker/         applications.csv (ignored)
templates/       resume.typ (Typst template)
scripts/         the `hj` CLI
```

## Status
Working: search (+YC), the feedback loop, `assess`/`rate`/cards, main-resume validator, draft checks, tracker.
**Not yet exercised end to end:** `hj build` (needs Typst), `hj intake`, `hj apply` (needs Chromium); per-ATS form
adapters beyond a generic one are not written. Ranking is a work-in-progress heuristic.
