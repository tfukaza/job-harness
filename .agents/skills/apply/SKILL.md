---
name: apply
description: Build the approved resume PDF and open the application portal with the form pre-filled and resume attached, then hand off to the user to submit. Use after the user approves a draft.
---

# Apply

Preconditions: `jobs/<slug>/draft.yaml` has `approved: true` (set by the user). If not, stop and say so.

1. `uv run hj build jobs/<slug>`; tell the user the PDF path and ask them to open and check it. Wait for confirmation.
2. Get the application URL from `job.md`. Run `uv run hj apply jobs/<slug> <url>` (interactive; it fills fields, attaches the PDF, then pauses).
3. **Never click Submit.** The user reviews every answer and submits themselves.
4. After the user confirms they submitted, run `uv run hj track add "<company>" "<role>" --url <url> --resume jobs/<slug>/resume.pdf`.
5. Don't log an application the user didn't confirm submitting.
