---
name: resume-layout
description: Make a tailored resume look polished - exactly one full page, easy to scan, key words in bold. Run after tailor-resume writes draft.yaml, and whenever the user says the resume looks off. Simple enough for small/cheap models - follow the numbers the build prints.
---

# Resume layout

**The code owns the layout. You own the content.** `templates/resume.typ` fixes fonts, margins, colors and spacing;
the font is fixed at 10pt and `hj build` only nudges spacing slightly; filling the page is your job, done with content. You never edit the template, font sizes or spacing.
You only choose which bullets go in, tighten their wording, and pick `keywords`. Every rule from `resume-style` and
AGENTS.md still applies (never invent facts; every bullet keeps its `source`).

## Personal style (fonts, monospace info, colors)
The user's look lives in `main/resume-style.yaml` (gitignored; template `main/resume-style.example.yaml`, defaults in
`templates/styles/`: `traditional` (Times New Roman) is the default, `rails` and `classic` the alternatives; pick one with `base:` and override keys). Keys: `body_font`, `mono_font` (lists, tried in order), `mono_for` (which info is
monospaced: `contact`, `dates`, `skills`, `tagline`), `mono_scale`, `accent`, `muted`.
Also: `text_color`, `display_font`/`display_bold` (name + headings), `heading_color`/`heading_case`/
`heading_tracking`, `rule` (solid/dashed/none) + `rule_color`, `rails` + `rail_color` + `rail_style` (solid/dashed), `rule_span` (text/page), `joints` + `joint_radius`
(circles where rules cross rails), `font_paths` (extra font folders), `spacing` (air between blocks; more air means
less content fits, so expect an OVER verdict and cut the least relevant bullets).
Full key list: `templates/styles/classic.yaml`. To show the user another preset without touching their file:
`uv run hj build --preview --style <preset> jobs/<slug>`. Samples of each: `docs/samples/`. To match a site the user points to, read its CSS variables
(colors, fonts, letter-spacing, borders) and map them onto these keys. When the user states a taste
("use font X", "dates in mono", "make headings green"), edit that file, never the template, then rebuild. If a font is
not installed, tell the user how to install it (e.g. `brew install --cask font-geist font-geist-mono`). Wider fonts can
change the fit, so rerun the loop below after any style change.

## Loop (at most 4 rounds)
1. `uv run hj build --preview jobs/<slug>` (works on unapproved drafts; writes `preview.pdf` and `preview-1.png`).
2. Read the first verdict line and do exactly what it says:
   - `OVER` -> remove the least relevant bullet(s) for this job (or merge two short related ones). Never shrink text.
   - `UNDER` -> add the next most relevant bullet(s) from `main/main.yaml` (unused sub-bullets of chosen items, then
     another project). Each new bullet needs `source` + `rationale`. If nothing relevant is left, add a short `tagline`
     to a project, or accept it and tell the user.
   - `OK` -> fix the `warn:` lines, then go to step 3.
3. Fix every `warn:` line:
   - "last line is only a word or two" -> cut words so it fits on one line, or (only with true detail from main.yaml)
     lengthen it to a fuller second line. Cutting is usually better.
   - "N lines" -> split into two bullets (both from the same source) or tighten.
   - keyword warnings -> fix the `keywords` list (exact, case-sensitive text that appears in a bullet).
   - mixed periods -> drop the trailing period from every bullet.
4. Rebuild. When the verdict is `OK` with no warnings, open `preview-1.png` and look at it once (step "Final look").

## Content rules that make it look good
- **One page, 95-100% full.** No big empty band at the bottom, nothing on page 2.
- **Bullets: 1 line ideal, 2 max.** Start with a strong verb (`resume-style`), one idea per bullet, include a number
  when main.yaml has one. No trailing period.
- **Counts:** 4-8 bullets for the current/most relevant role, 2-4 for older roles, 1-3 per project. Most relevant first.
- **Order inside a role:** the bullet that best matches the job's must-haves goes first.
- **Keywords (bold):** put a `keywords:` list in draft.yaml, 8-15 items total, at most 2 per bullet. Choose short
  phrases (1-3 words) that are both (a) in the job's requirements and (b) literally in your bullet text and true per
  main.yaml: tools (`Kubernetes`, `PostgreSQL`), techniques (`event-driven architecture`), outcomes (`p99 latency 40%`).
  Never bold whole sentences, generic words ("developed", "team"), or anything not in the posting's language.
- **Skills:** a mapping of 2-4 groups, most relevant group first, e.g.
  `skills: {Backend: [gRPC, ...], Languages: [Python, ...], Infra & tooling: [Docker, ...]}`.
  Only items from main.yaml's skills (or tools named in included bullets).
- **Header:** name + contact list. Contact items short: `github.com/user`, `linkedin.com/in/user`, no `https://`.
  The template keeps it on one line.
- **GPA:** if main.yaml has a GPA of 3.5 or higher, add it to the degree line (`B.S. Computer Science, GPA 3.7`).
  Below 3.5 or not recorded: leave it off. Use the exact value from main.yaml.
- **Dates:** one format everywhere: `2021 – present`, `2026 – present`, `2021`.
- **Section order:** Summary, Experience, Projects, Education, Skills (Education goes right after Summary only for new
  grads/interns). Summary: 1-2 lines, specific to the role.
- **ATS-safe by construction:** single column, real text, no tables, icons, photos or graphics. Do not add any.

## Final look (`preview-1.png`)
Check, and fix by editing content then rebuilding:
- Bold words are spread out (not three in one corner), and each one is a term the posting asks for.
- No line with a lone word; no bullet that looks much longer than its neighbors.
- Spacing looks even; no section with a single orphan bullet at the very bottom.
Then tell the user: the verdict line, what you added/cut and why, and show the PNG. The draft stays
`approved: false`; the user approves, then `uv run hj build jobs/<slug>` makes the final `resume.pdf`.
