---
name: find-jobs
description: Discover and score new job postings against the user's criteria and main resume, adding them to search/inbox.csv for triage. Use when the user wants to look for jobs.
---

# Find jobs

1. Run `uv run hj search` (pulls from `search/companies.yaml` via public Greenhouse/Lever/Ashby APIs, filtered by `search/criteria.yaml`, deduped against inbox and tracker).
2. If the user wants broader coverage, use WebSearch for roles matching `criteria.yaml` outside the watchlist; add promising companies' ATS board slugs to `search/companies.yaml` (tell the user what you added). Do not scrape LinkedIn/Indeed.
3. For each row in `search/inbox.csv` with `decision=new` and empty `fit_score`: read the posting, compare with `main/main.md`, and fill `fit_score` (1-5) and a one-line `fit_note` (strengths and gaps).
4. Show the user a ranked summary. **Leave `decision` as `new`**; the user marks `interested` or `skip`.

Never apply or run `new-job` without the user picking postings.
