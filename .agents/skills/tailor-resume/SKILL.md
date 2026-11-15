---
name: tailor-resume
description: Tailor the main resume to a specific job and company. Researches the company and role first, builds a relevance map against main/main.yaml, then writes jobs/<slug>/draft.yaml with a rationale per pick. Use when the user wants a resume for a job.
---

# Tailor resume

Input: a job directory (`jobs/<slug>/`). If not given, use the most recent one.
Follow `resume-style` for wording and `resume-layout` for the page. Never add facts (AGENTS.md rule 2).

## 1. Research the company and the role (do not skip)
The posting alone is not enough: it is generic, and it hides what the company really builds. A harness company, a
fintech and a game studio need different bullets even for the same title.
- Read `jobs/<slug>/job.md` fully. List must-haves and nice-to-haves **in the posting's own words**.
- Learn the company: WebSearch / WebFetch their site, product page, engineering blog, launch posts, and what they
  publish (benchmarks, research, open source). Standard searches are enough; prefer the company's own pages and
  say when a claim comes only from third-party coverage. Answer in a few lines:
  1. What do they build, and what is the *core technical bet*? (e.g. "the agent harness is the product")
  2. What problems will this role's team face in practice (scale, reliability, evals, security, latency...)?
  3. Which terms do they use for their own concepts? (reuse them only where true for the user)
  4. Any signal about the team's stage/culture (research-y, enterprise, early startup)?
- Send nothing about the user to outside services: search only for the company and role. Never put the user's name,
  employer, or resume text in a query.
- Save the findings as `jobs/<slug>/research.md` (short, with source links). It stays local (gitignored).

## 2. Build a relevance map before writing anything
Read all of `main/main.yaml`, including **projects and side projects, not only the job history**. For each
experience, project and bullet, write a one-line verdict against the research:
- `core`: directly what the company builds or the role does (same kind of system, same problems)
- `support`: shows a needed skill (evals, reliability, tooling, languages they use)
- `skip`: true but not relevant
Rules for the map:
- **Judge by what the company builds, not only by posting keywords.** If the company's product is X, anything the user
  built that is X or X-adjacent is `core`, whether it was paid work or a side project.
- **Side projects count equally.** A recent project that is the same kind of system as the company's product often
  beats an older job's bullet. Do not relegate projects to filler.
- Use the `tags` in main.yaml to find candidates, then read the text; tags are hints.
- Save the map in the draft's `rationale` fields and `omitted` list (don't create a separate file).

## 3. Select and shape
- Fill the page by relevance: `core` items first and in depth (3-5 bullets for a core project), then `support`.
  If core projects are strong, give them as much room as a job; consider fewer bullets for the current job if its
  remaining bullets are only `support`.
- Pick the framing the company would recognize, using their vocabulary where it is true.
- Lead each entry with its most relevant bullet. Lightly polish wording; **do not add facts, tools, titles, dates or
  numbers not in the main resume**. Keep caveats from `note:` fields honest (pilot, single run, scripted).
- A one- or two-line `summary` specific to this company and role, using only facts from main.yaml. No pronouns.
- Add `keywords:` and grouped `skills:` (see `resume-layout`).

## 4. Write `jobs/<slug>/draft.yaml`
Follow `jobs/example/draft.yaml`:
- `approved: false` (always; only the user flips it)
- every bullet has `source` (main id) and `rationale` that says *why this matters to this company*
- an `omitted:` list for notable items left out, with why

## 5. Layout, then hand off
- Run the `resume-layout` skill: `uv run hj build --preview jobs/<slug>` until the verdict is `OK` with no warnings.
- Self-check before showing the user: are the items marked `core` actually the most prominent on the page? Would the
  hiring manager see their own product's problems in the first third? If not, revise.
- Show `preview-1.png`, the research findings (3-5 lines), and what you chose to emphasize and why.
- Tell the user to review/edit `draft.yaml`, set `approved: true`, then run `uv run hj build jobs/<slug>`.

`build --preview` is always fine. Never run the final build or apply yourself until the user confirms the draft is approved.
