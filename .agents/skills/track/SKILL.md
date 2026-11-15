---
name: track
description: View and update the application tracker (statuses, notes) and summarize the pipeline. Use when the user asks about application status or reports an update like a rejection or interview.
---

# Track

- List: `uv run hj track list [--status interview]`; detail: `uv run hj track show <id>`
- Update: `uv run hj track status <id> <applied|screen|interview|offer|rejected|withdrawn> --note "..."`
- Summarize the pipeline by status, and flag applications with no update in 14+ days (compare `updated` to today) as follow-up candidates.

Only change a status when the user reports it.
