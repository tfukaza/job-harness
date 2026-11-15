---
name: find-jobs
description: Iterative job hunt. Pull postings, score a few candidates against the main resume and past feedback, show them, record the user's likes/dislikes, and apply what was learned to the next round. Use when the user wants to look for jobs.
---

# Find jobs (iterative, feedback-driven)

> **WIP:** the ranking algorithm is a first draft (title-word/company/city weights plus your `fit_score`). Treat
> scores as hints, tell the user when a ranking looks off, and expect this skill to change.

State lives in gitignored files: `search/inbox.csv` (postings), `search/feedback.csv` (every verdict + reason),
`search/preferences.yaml` (learned weights, hard blocks, notes). Read `hj prefs` first so the new round uses past feedback.

## One round
1. **Learn context.** `uv run hj prefs`. Read the notes, blocks, and the recent verdicts with reasons.
2. **Pull.** `uv run hj search` (add `--yc` for YC startups). Blocked companies/titles are dropped automatically.
   For wider coverage, WebSearch roles matching `search/criteria.yaml` outside the watchlist; add ATS slugs to
   `search/companies.yaml` and say what you added. No LinkedIn/Indeed scraping.
3. **Assess, then score only what you will show.** Level and experience are read by a cheap LLM, never by regex
   (postings word this in too many ways). Run `uv run hj assess --pending -n 15`: it fetches each posting
   (ATS JSON when possible), and Haiku returns the *required* years, the seniority the role really expects
   (judged from scope and pay, not the title), whether it welcomes all levels, and a quote as evidence. These
   are written to the inbox; `hj batch` then applies `years_required` / `levels` from `criteria.yaml` in plain code.
   Compare with the user's `have_years`, **not their job title**: titles inflate or deflate differently per company
   (a "Senior Staff" at one firm can be about 5 years of experience). Postings that state no years, or span levels, stay visible.
   Spot-check the evidence quotes; fix a wrong one with `uv run hj level <id> <years> -n "<why>"`.
   If `hj assess` fails on credentials (needs `ANTHROPIC_API_KEY` or `ant auth login`), tell the user; as a
   fallback, read the postings yourself and record with `hj level`, but do not write regexes to do it.
   Then take `uv run hj batch -n 15`, read each posting against `main/main.yaml` and the preference
   notes/reasons, and fill `fit_score` (1-5) and a one-line `fit_note` (strength + gap) in `search/inbox.csv`.
   Do not score the whole inbox.
4. **Show a small batch.** `uv run hj batch -n 5`. Present id, company, title, location, score, note, URL.
   Do not mark anything yourself (AGENTS.md rule 4).
5. **Collect feedback.** Ask the user, per posting, like or dislike plus a short *why* (the reason matters more
   than the verdict). Record each: `uv run hj feedback <id> like|dislike -r "<reason>"`.
   This sets `decision` to interested/skip and nudges the learned weights.
6. **Distill.** From the new reasons, edit `search/preferences.yaml`:
   - repeated company/title-type rejections -> `block_companies` / `block_title` (confirm with the user first);
   - stated tastes ("wants infra over product", "no ad-tech", "min seniority senior") -> `notes` as one short line each;
   - tell the user what you changed. Also update `search/criteria.yaml` if a rule belongs there (titles, locations).
7. **Next round.** Offer another batch; steps 1-5 repeat and the learned weights/notes shape ranking and scoring.

## Rules
- Leave undecided rows as `new`. Only the user's feedback changes `decision`.
- Never run `new-job` or `apply` until the user picks a posting they liked.
- Keep batches small (3-5) so feedback stays specific.
