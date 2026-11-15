# job-harness

A human-in-the-loop job application harness. You keep **one big "main" resume**. An AI agent finds postings,
picks and rewords the right bullets for each job, builds a PDF, and fills in the application form. **You review
every step and press Submit yourself.** Nothing is sent without you.

```
main resume ─► find jobs ─► you pick ─► tailored draft ─► you approve ─► PDF ─► form filled ─► you submit ─► tracker
```

It is plain Python plus markdown playbooks, so it works with any coding agent (Claude Code, Codex, ...). The
deterministic work is a CLI (`uv run hj ...`); the agent only does the judgment steps (scoring fit, tailoring wording).

## What it will never do
- Click Submit, Apply or Send. Adapters stop before submission.
- Invent facts. Every resume bullet must trace to an id in your `main/main.yaml`; `hj build` rejects anything else.
- Use a draft you haven't approved (`approved: true` is yours to set).
- Mark a posting `interested` or an application `applied` without you saying so.
- Commit your personal data. `main/`, `jobs/`, `tracker/` and your search results are gitignored.

## Status
Working: job search (Greenhouse, Lever, Ashby APIs plus YC discovery), the iterative feedback loop, the main-resume
validator, draft checks, tracker.
**Not yet exercised end to end:** `hj build` (needs Typst), `hj intake`, and `hj apply` (needs Chromium). Per-ATS form
adapters beyond a generic one are not written. Job ranking is a **work-in-progress heuristic**: treat scores as hints.

## Setup (about 10 minutes)

**You need:** [uv](https://docs.astral.sh/uv/), Python 3.10+, and a coding agent. For PDFs: [Typst](https://typst.app).
For form filling: Chromium via Playwright. For `hj assess`: an `ANTHROPIC_API_KEY`.

```bash
git clone https://github.com/tfukaza/job-harness && cd job-harness
uv sync
brew install typst                      # or see typst.app; needed for `hj build`
uv run playwright install chromium      # needed for `hj apply`

# your private files (all gitignored): copy the templates, then fill them in
cp main/main.example.yaml main/main.yaml            # your whole resume, every bullet; see "Main resume" below
cp main/profile.example.yaml main/profile.yaml      # or let the agent interview you (next line)
cp search/criteria.example.yaml search/criteria.yaml
cp search/companies.example.yaml search/companies.yaml

export ANTHROPIC_API_KEY=...            # only for `hj assess` (a cheap model reads postings)
uv run hj check                         # validates main/main.yaml; fix anything it reports
```

Then open the repo in your agent and say: **"run the setup-profile skill"**. It asks the questions portals keep
asking (work authorization, location, salary, ...), shows a summary, and writes `main/profile.yaml` only after you say yes.

## Daily use
Talk to your agent in plain language; each step maps to a skill in `.agents/skills/`.

| You say | Skill | What happens | Your gate |
|---|---|---|---|
| "find me jobs" | `find-jobs` | Pulls postings, checks the experience each one really requires, shows 3-5 candidates | like / dislike each, with a reason |
| "apply to `<id or url>`" | `new-job` | Saves the posting to `jobs/<slug>/job.md` | |
| "tailor my resume" | `tailor-resume` | Writes `jobs/<slug>/draft.yaml` with a rationale per pick | edit it, set `approved: true` |
| "build it" | (`hj build`) | Renders `resume.pdf` | open and check the PDF |
| "fill the application" | `apply` | Opens the portal, fills it, attaches the PDF, **pauses** | you click Submit |
| "what's my pipeline" | `track` | Updates and summarizes `tracker/applications.csv` | |

### The job-hunt loop (feedback improves the next round)
1. The agent pulls postings (`hj search`, add `--yc` for Y Combinator startups) and reads each candidate with a cheap
   model (`hj assess`) to extract required years, real seniority and pay.
2. `hj batch` shows the top few. You answer like or dislike **and why**; the agent records it with `hj feedback`.
3. Weights and notes land in `search/preferences.yaml`, which shapes ranking and scoring next time.

Seniority is judged by **years required**, not titles (titles inflate differently at every company). Set your range in
`search/criteria.yaml` (`years_required: {min, max}`). Postings that state no years, or welcome all levels, stay visible.

## Main resume
`main/main.yaml` is the single source of truth: experience, projects, education and skills, with a stable `id` and
`tags` on every bullet. Include everything; tailoring picks from it. `main/main.example.yaml` shows the schema, and
`uv run hj check` flags duplicate ids, empty text, placeholders like `TODO`/`XX%`, and open `note:` fields.
Bullet wording follows the `resume-style` skill (based on Harvard's resume guide, credited in the skill).

## Commands
Run as `uv run hj <command>`.

| Command | Purpose |
|---|---|
| `search [--yc]` | Pull new postings into `search/inbox.csv` (filters from `criteria.yaml`) |
| `assess [ids] [--pending -n 15]` | A cheap LLM reads postings: required years, seniority, pay (needs `ANTHROPIC_API_KEY`) |
| `batch [-n 5]` | Top undecided postings, ranked with what you've taught it (WIP ranking) |
| `feedback <id> like\|dislike -r "why"` | Record a verdict; updates inbox and learned preferences |
| `prefs` | Show learned weights, blocks, notes, recent verdicts |
| `level <id> <years> -n "why"` | Manually set a posting's required years |
| `intake <url\|id>` | Create `jobs/<slug>/job.md` |
| `check [job-dir]` | Validate `main/main.yaml` (and a draft's source ids) |
| `build <job-dir>` | `draft.yaml` -> `resume.pdf` via Typst; refuses unapproved drafts |
| `apply <job-dir> <url>` | Open the portal, fill, attach the PDF, **pause** for you |
| `track add\|status\|list\|show` | Application tracker (`applied, screen, interview, offer, rejected, withdrawn`) |

## Layout
```
main/            main.yaml, profile.yaml (yours, ignored) + *.example.yaml templates
search/          criteria.yaml, companies.yaml (yours); inbox.csv, feedback.csv, preferences.yaml (generated, ignored)
jobs/<slug>/     job.md, draft.yaml, resume.pdf per application (ignored; jobs/example is a tracked sample)
tracker/         applications.csv (ignored)
templates/       resume.typ (Typst template)
scripts/         the `hj` CLI
.agents/skills/  playbooks any agent can follow (.claude/skills is a symlink to it)
AGENTS.md        the rules every agent must obey (CLAUDE.md just imports it)
```

## For agents
Read `AGENTS.md` first (hard rules and command list), then the skill that matches the task in
`.agents/skills/<name>/SKILL.md`. Use the `hj` CLI for anything deterministic. Never write regexes to interpret
posting text; use `hj assess`. Stop and ask the user at every ⛔ gate above.

## Credits
`resume-style` paraphrases the [Harvard College Guide to Creating a Strong Resume](https://careerservices.fas.harvard.edu/resources/create-a-strong-resume/)
(Harvard FAS Mignone Center for Career Success); Harvard has not endorsed this project. YC company discovery uses the
community [yc-oss](https://github.com/yc-oss/api) dataset.
