---
name: new-job
description: Start work on a job: create jobs/<slug>/job.md from an inbox id or URL, then tailor the resume. Use when the user names a job posting to apply to.
---

# New job

1. Run `uv run hj intake <url|inbox-id>` (add `--company`/`--role` for raw URLs).
2. Open `jobs/<slug>/job.md`; if the fetch failed or looks thin (JS-rendered page), ask the user to paste the description, or fetch it with WebFetch, and update the file.
3. If the inbox row was used, set its `decision` to `interested` only if the user said so.
4. Continue with the `tailor-resume` skill.
