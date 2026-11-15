---
name: tailor-resume
description: Tailor the main resume to a specific job. Reads jobs/<slug>/job.md and main/main.md and writes jobs/<slug>/draft.yaml with a rationale per pick. Use when the user wants a resume for a job.
---

# Tailor resume

Input: a job directory (`jobs/<slug>/`). If not given, use the most recent one.

1. Read `jobs/<slug>/job.md` and `main/main.md` (and `main/profile.yaml` for header details).
2. Extract the role's must-haves and nice-to-haves.
3. Select the most relevant experience, projects, and skills from the main resume. Prefer impact and specificity. Aim for one page.
4. Lightly polish wording (clarity, active voice, mirror the job's terminology where truthful). **Do not add facts, tools, titles, dates or numbers not in the main resume.**
5. Write `jobs/<slug>/draft.yaml` following `jobs/example/draft.yaml`:
   - `approved: false` (always; only the user flips it)
   - every bullet has `source` (main id) and `rationale`
   - an `omitted:` list for notable items left out, with why
6. Tell the user to review/edit `draft.yaml`, set `approved: true`, then run `uv run hj build jobs/<slug>`.

Never run build or apply yourself until the user confirms the draft is approved.
