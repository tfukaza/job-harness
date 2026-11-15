# Job Harness: rules for any coding agent

This repo turns `main/main.yaml` into tailored resumes and helps apply. **Human-in-the-loop is non-negotiable.**

## Hard rules
1. **Never click Submit / Apply / Send** on any portal. Adapters stop before submission; the user submits.
2. **Never invent facts.** Every bullet in a `draft.yaml` must trace to `main/main.yaml`. You may reword for clarity, relevance and concision; you may not add employers, titles, dates, skills, tools, or metrics that are not in the main resume.
3. **Always go through the draft.** Write `jobs/<slug>/draft.yaml` with `approved: false` and a `rationale` for every pick and notable omission. Only the user sets `approved: true`. `hj build` refuses otherwise.
4. Do not mark anything `interested` in `search/inbox.csv` or change tracker status to `applied` without the user saying so.
5. Personal data (`main/`, `jobs/`, `tracker/`, `search/inbox.csv`) is gitignored. Never commit or send it elsewhere.

## Commands (`uv run hj ...`)
- `search`: pull postings from `search/companies.yaml`, filter by `search/criteria.yaml`, append to `search/inbox.csv`
- `batch [-n 5]`: top undecided postings (level-filtered, ranked with learned preferences). **Ranking is WIP**: a crude heuristic, so treat scores as hints, not decisions
- `feedback <id> like|dislike -r "why"`: record the user's verdict; updates inbox + `search/preferences.yaml`
- `assess [ids] [--pending -n 15]`: a cheap LLM (Haiku, needs `ANTHROPIC_API_KEY`) reads postings and records required years, real seniority, pay; `batch` filters by `years_required`/`levels` in criteria. No regex over posting prose
- `level <id> <years> -n why`: manual override of a posting's required years
- `prefs`: show learned weights, blocks, notes, recent verdicts
- `intake <url|inbox-id>`: create `jobs/<slug>/job.md`
- `build <job-dir>`: draft.yaml -> resume.pdf via Typst (needs `typst` on PATH)
- `apply <job-dir>`: open portal, fill, attach PDF, **pause** for the user to submit
- `check [job-dir]`: validate `main/main.yaml` (and a job's draft sources)
- `track add|status|list|show`: manage `tracker/applications.csv`

## Skills (agent-agnostic playbooks)
Plain-markdown playbooks live in `.agents/skills/<name>/SKILL.md`: `setup-profile`, `find-jobs`, `new-job`, `tailor-resume`, `resume-style`, `apply`, `track`.
If your agent has no native skill loader, read the matching file and follow it as written.
(`.claude/skills` is a symlink to `.agents/skills`, so Claude Code, Codex, and others all pick them up.)
All deterministic work is in the `uv run hj ...` CLI; the agent only does judgment steps (scoring fit, tailoring, polishing wording).
