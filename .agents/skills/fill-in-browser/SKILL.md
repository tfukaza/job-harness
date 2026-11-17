---
name: fill-in-browser
description: Fill a job application in the user's own browser (their sign-ins, Google/LinkedIn sessions) using whatever browser or computer-use tool this agent has - Claude in Chrome, Claude or Codex computer use, cmux-cua, chrome-devtools MCP, or similar. Default way to apply when main/mode.yaml has browser agent.
---

# Fill in the user's browser (tool-agnostic)

The harness decides **what** goes in the form and **whether** Submit is allowed. You decide **how** to click and type
with the tool you have. Never solve or bypass a CAPTCHA or bot check; never accept legal agreements for the user.

## 0. Prove the answers fit the form first
`uv run hj fill-check jobs/<slug> <posting-url>`: fills the real form in a hidden browser from answers.yaml, reads
every field back, saves `fill-check.png`, never submits. Fix every MISSING / CHECK / FAIL row (wrong option text,
follow-up questions that appear after an answer, missing answers) until it prints `READY`. Only then fill the
user's browser. It also catches embedded forms (company sites that wrap Greenhouse/Lever/Ashby in an iframe).

## 1. Get the plan
`uv run hj plan jobs/<slug> <posting-url>` -> prints and writes `jobs/<slug>/fill-plan.md` (+ `.json`): the URL, each
question with the exact value (or the file to upload), and `Submit: allowed` or `NOT allowed` with reasons.
Needs `form.json` (`hj form`), `answers.yaml`, and the final `resume.pdf` (`hj build`).

## 2. Pick your tool (first one available wins)
1. A tool that reads the page structure in the user's real browser (e.g. Claude in Chrome, a browser extension,
   chrome-devtools MCP attached to the user's Chrome). Prefer it: fields are found by label, not by pixels.
2. Computer use on the user's desktop (Claude computer use, Codex computer use, cmux-cua, or any other). Use the
   user's normal browser window. Prefer accessibility-tree element targeting over raw coordinates when offered.
3. None available: tell the user, and offer the Playwright fallback (`hj apply`, set `browser: playwright`).
Load your tool's own skill or instructions first if it has one (e.g. its safety rules for logged-in sites).

## 3. Fill (hybrid: script for the basics, you for the rest, script to verify)
Order matters. Many forms parse the uploaded resume and overwrite fields, so:
1. **Upload the resume first** (see "File upload" below) and wait until the file name shows.
2. **Run `jobs/<slug>/fill.js`** in the tab with your tool's run-JavaScript ability (Claude in Chrome javascript
   tool, cmux-cua `page` execute_javascript, chrome-devtools evaluate_script, or paste into DevTools console).
   It fills text fields, text areas, native selects and Yes/No buttons, reads them back, and returns a report
   (also in `window.__hjFill`): `filled`, `needs_agent` (each with an exact instruction), `unmatched_questions`.
3. **Do every `needs_agent` item yourself with real clicks/typing**: custom dropdowns and autocompletes ignore
   scripted events, so click the field, type the value, pick the matching option.
4. **Run `fill.js` again** if any answer may have revealed follow-up questions (e.g. race after Hispanic/Latino).
5. **Run `jobs/<slug>/verify.js` (final check, changes nothing).** `ready: true` only when every planned answer is
   visible, no required field is empty, and no question is unanswered. Fix whatever it lists, run it again.
   Never submit without `ready: true`.
Without a run-JavaScript ability, do steps 2-5 by hand from `fill-plan.md`, then read the page back yourself.

## 3b. Manual details
- Open the plan's URL in a **new tab** of the user's browser. Do not touch other tabs.
- For each row in order: find the field by its question text, set the value exactly, then **read it back**.
  Dropdowns: pick the listed option text. Autocomplete fields: type, then choose the matching suggestion.
- **File upload** (resume): use your tool's upload action if it has one (e.g. an upload_file on the input).
  With pure computer use, click the upload button, then in the macOS file dialog press Cmd+Shift+G, paste the
  absolute path from the plan, Enter, Enter. On Windows/Linux, paste the path into the file-name box.
  Confirm the page shows the file name afterwards.
- Do **not** click "Apply with LinkedIn/Google" or similar autofill unless the user asks: it overwrites answers.
  If the user's own autofill (browser, password manager) changes a field, set it back to the plan's value.
- Anything the plan does not cover (a new question, an attestation, a legal agreement): stop and ask the user.

## 4. Submit or hand over
- Take a screenshot of the filled form (save it as `jobs/<slug>/form-filled.png` if your tool can).
- `Submit: NOT allowed` (e.g. review mode): stop, tell the user it is ready for them to review and submit.
- `Submit: allowed` (assist/yolo mode, all gates passed): click Submit **once**. Then:
  - Confirmation page ("submitted", "thank you"): screenshot it, then `uv run hj submitted jobs/<slug>`.
  - CAPTCHA / "verify you are human" / "error verifying your application": stop, ask the user to finish in the
    same tab, and log with `hj submitted` only after they confirm. Never retry in a loop.
  - Validation errors: fix only fields covered by the plan, otherwise hand over.
- Never log an application that was not confirmed.

## Tested recipe: custom dropdowns (Greenhouse react-select; verified 2026-11-15)
For each `needs_agent` dropdown: real click on the combobox -> type the search text -> read the options **inside the
active field only** (`document.activeElement.closest('.select__container')`; the phone country list keeps hidden
`[role=option]` elements on the page all the time) -> confirm the focused option is the exact answer (typing "Male" also
shows "Female") -> press Enter. City lookups load suggestions asynchronously: wait ~2s before reading them.

## Which systems are verified (dry-run on live postings, 2026-11-15)
| System | Status |
|---|---|
| Ashby, Greenhouse (incl. forms embedded on company sites), Lever | `fill-check` READY end to end. Lever: the user clicks Submit (bot check) |
| Gem, Workable, Recruitee | `fill-check` works with the generic reader (`blocks.js`): text, radios, uploads, textareas. Recruitee and some others hide the form until Apply is clicked; `hj` clicks it, in your own tab you must click Apply first, then run `fill.js` |
| SmartRecruiters | Bot wall (DataDome slider/audio) blocks automated browsers, headless or not; the form never loads. Never try to pass it: the user opens it in their own Chrome, then `fill.js` + `verify.js` apply. No dry run |
| Workable | Also verified in a real agent-driven browser (upload, `fill.js`, `verify.js`); it prefilled a wrong address from the IP, `fill.js` overrides it |
| Workday | Needs a per-company account (user signs in); `fill.js` can fill the pages after sign-in |
| YC Work at a Startup | Needs the user's YC login; hand off |
| Notion pages, Google Forms, emails | Custom: read what they ask, fill nothing by script, ask the user |

Rules learned the hard way: (1) an option's text is always on the page, so a radio/checkbox/Ashby button only counts as
answered when it is **checked / aria-pressed**; (2) a lone `*` line is a required marker, not the question;
(3) element ids can contain `:`, so never use `#id` selectors, use `[id='...']`;
(4) always run `verify.js` last, `ready: true` is the only green light.

## Pixel-level computer use on the user's own Chrome (cmux-cua)
For anti-bot sites (SmartRecruiters/DataDome) that only load in the user's own Chrome. Works, but only with this recipe
(found by testing against a throwaway page whose real values were read through DevTools; see `AGENTS.md` skills):
1. `bring_to_front` the window first. A hidden/off-screen window returns a **stale screenshot** and the driver still
   says `confirmed`. Never trust `verified`/`confirmed`; judge by a fresh screenshot, and expect a repaint lag (take
   one more if the right side looks blank or a value looks old).
2. Every action `delivery_mode: "foreground"` (background drops keystrokes). Chrome's AX tree has no page content, so
   click by screenshot pixels (x, y in the screenshot's own coordinates).
3. To fill or replace a field: `click` with `count: 3` (selects its contents), then a pause (a `get_window_state` call
   with `include_screenshot: false`), then `type_text` with `delay_ms: 150`. At the default 30 ms the first capital letter
   is dropped; right after a click on another field it can be dropped even at 100 ms, hence the pause.
4. Cmd+A / Cmd+Delete / Cmd+Shift+G do NOT work (Chrome handles them through its menu, which synthetic key events skip).
   Use triple-click to select. Plain keys (Backspace, Escape, letters) do arrive.
5. Dropdowns: click to open, `type_text` the search text, screenshot, click the right option.
6. After each field take a screenshot and compare to the answers file. Fix only what is wrong.
7. File dialogs (native Open panel) open fine, but the Go-to-folder shortcut does not; typing "/" is untested, and Cancel
   by click/Escape could not be confirmed. Put the file where the dialog opens (e.g. Desktop/Downloads) or ask the user to
   pick it.
8. Never click Submit by pixels unless `verify.js`-equivalent checks (every answer visible, no required field empty) pass.
