---
name: write-answers
description: Write free-text answers on application forms ("Why are you interested in X?", "Tell us about a project", "Anything else?") in the user's own voice, grounded in their resume and the company research. Use whenever answers.yaml has a textarea or open question.
---

# Write answers in the user's voice

You write the whole answer; the goal is that it reads as written by the user, not by an AI.

## Voice setup (once, then reuse)
- `main/voice.md` is the user's voice card (register, rhythm, words they use, a never-use list, exemplars).
- Missing or stale? `uv run hj voice collect` (gathers, locally only: messages the user typed to coding agents,
  their own pre-AI repo prose and commits, resume bullets -> `main/voice/samples.md`; sources in `main/voice.yaml`).
  Then have a strong-model subagent distill `samples.md` into `main/voice.md` and show it to the user once.
- Samples and the card are personal data: never commit, quote or send them anywhere outside this machine.

## Answer the question (the most important rule)
An answer is not a resume summary. Work out what the question is really asking, answer **that** in the first
sentence, and use the user's experience only as evidence for the answer (at most about a third of the words).
Test: could this text be pasted under a different question unchanged? Then it does not answer this one.
Tone: interested, not enthusiastic (voice card section 0). Lead with the most interesting specific (an opinion,
the problem itself, a tradeoff) so the answer is worth reading. Interest is about the work, never about metrics,
benchmarks, funding or prestige. Then run the `review-answers` panel before the answer is used.

What each common question is really asking:
- **Why this company / why are you interested?** What about *this company* draws the user: its product, its
  technical bet, how it works, what it publishes (from research.md), connected to what the user already chooses
  to work on. Their experience proves the interest is real; it is not the answer.
- **Why this role / what would you work on?** What the role's work is, and why that work fits what the user wants
  to do next.
- **Tell us about a project / something you built.** One project, told as: the problem, what the user did, a
  decision or tradeoff they made, the result. Not a list of projects.
- **A challenge / failure / disagreement.** One specific situation, what the user did, what they learned or would
  do differently. Must come from a real item; if main.yaml has no such story, stop and ask the user.
- **What are you looking for / goals?** What the user wants next, from their stated preferences.
- **Anything else we should know?** One useful thing not already on the resume, or skip if optional.
Motives and preferences are facts too: take them from `main/motivations.md` first (the user's own words), then
`search/preferences.yaml` notes and feedback reasons; never invent feelings, opinions or lessons learned. If the
real motive is unknown: in review and assist modes ask the user and add their answer to `main/motivations.md`;
in yolo mode use only what is recorded, or stop.

## Per question
1. Read the question (and any word/character limit), `research.md`, `job.md`, `draft.yaml`, `main/main.yaml`,
   `main/profile.yaml`, `main/motivations.md`, and `main/voice.md`.
2. Decide the answer first (see above), then pick evidence: 1-2 true things the user did (main.yaml ids) and the
   specific company facts (research.md) that support it. One real company fact beats three generic ones.
   No invented motives, history, feelings or numbers.
3. Write it in the voice card, at the register its section 0 sets (the user wants applications a bit more formal
   than their everyday voice; if the user asks to change formality, edit section 0, not the exemplars): first person, plain words, the user's sentence length and connectors. Default
   60-120 words unless the form says otherwise. No greeting, no sign-off, no restating the question.
4. Self-check, rewrite until all pass:
   - the first sentence answers the question; experience is supporting evidence, not the bulk
   - nothing from the never-use list; no sentence that would fit any other company
   - every claim traces to main.yaml / profile.yaml / research.md
   - read it next to 2-3 exemplars from voice.md: same person?
5. In `answers.yaml` record `source:` (main ids + research.md) and `voice: main/voice.md`.

Yes/no, dropdowns, and factual fields are not this skill: answer those from `profile.yaml` (see `apply`).
