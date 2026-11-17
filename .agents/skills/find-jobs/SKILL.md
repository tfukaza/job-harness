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
3. **Assess, then score only what you will show.** Run the `assess-postings` skill on about 15 candidates
   (cheap-model subagents read each posting; no regex, no API key). Compare with the user's `have_years`, **not
   their job title**: titles inflate or deflate differently per company (a "Senior" title can mean 3 years at one
   firm and 10 at another). Then take `uv run hj batch -n 15`, read each against `main/main.yaml` and the preference
   notes/reasons, and record your judgment with `uv run hj rate <id> -s <1-5> -w "<why it fits THIS user>"`
   (add `--summary` / `--comp` if assess did not fill them). Do not score the whole inbox.
   Then run the `estimate-comp` skill for the postings you will show: research each new company (2-sentence
   summary) and record a labeled TC estimate. Every card must carry both.
4. **Show a small batch in the standard card format.** `uv run hj batch -n 5` prints each job as a card
   (company + researched summary, role, stated comp, ESTIMATED TC, location, level, about, why it fits you, link); `uv run hj show <id>` prints one.
   Show cards exactly as printed, without dropping or reordering fields, so every job looks the same.
   If a card says "(not filled in yet)", fill it first (`hj rate ... --summary/--why`, `hj assess`), and write
   "Why you" about *this* user: cite their real experience from `main/main.yaml`, then name one gap.
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
