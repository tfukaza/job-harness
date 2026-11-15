---
name: resume-style
description: Style rules for writing and polishing resume bullets (action verbs, quantified results, plain language, formatting). Use whenever drafting, tailoring, or editing resume text, including main/main.yaml and jobs/<slug>/draft.yaml.
---

# Resume style

## Credit and scope
Based on the **Harvard College Guide to Creating a Strong Resume**, Harvard Faculty of Arts & Sciences,
Mignone Center for Career Success: https://careerservices.fas.harvard.edu/resources/create-a-strong-resume/
This is a paraphrased summary for personal use, not Harvard's text, and Harvard has not endorsed this repo.
Read the original for the full guidance, templates and sample resume. Items marked **(harness addition)**
are not from Harvard; they are this repo's own conventions.

## Language should be
- Specific rather than general.
- Active rather than passive ("Led X", not "X was led").
- Written to express, not impress; plain and articulate, not flowery.
- Fact-based: quantify (numbers, scale, time, percentages) and qualify (what changed, for whom).
- Easy to scan quickly, for both people and applicant-tracking systems.

## Top mistakes to avoid
1. Spelling and grammar errors.
2. Missing email or phone.
3. Passive language instead of action verbs.
4. Poor organization; not concise or skimmable.
5. Not showing results.

## Don't
- Use personal pronouns (I, we), narrative style, slang, or colloquialisms.
- Abbreviate (spell things out; widely known industry terms like "VPN" are fine, **harness addition**).
- Include a picture, age, gender, or references.
- Start each line with a date.

## Do
- Be consistent in format and content (spacing, bold, italics, capitalization).
- Keep it easy to read, balancing white space.
- Order headings by importance; within each, list items most recent first.
- Avoid unexplained gaps in dates.
- Check the layout survives conversion to PDF.
- Tailor to the type of position; show the skills the employer values.

## Action verbs
Start every bullet with a strong past-tense verb (present tense for current work). Harvard groups verbs by
theme; ones that suit engineering work (see the page for the full lists):
- Leadership: Led, Spearheaded, Orchestrated, Coordinated, Directed, Oversaw, Improved, Increased, Surpassed
- Technical: Built, Designed, Engineered, Optimized, Programmed, Streamlined, Standardized, Maintained, Upgraded, Overhauled, Solved
- Research: Investigated, Identified, Tested, Evaluated, Modeled, Diagnosed, Determined
- Organizational: Implemented, Launched, Generated, Reduced, Simplified, Expanded, Monitored, Validated, Verified
- Creative: Created, Established, Founded, Initiated, Integrated, Introduced, Invented, Redesigned
- Communication: Documented, Presented, Collaborated, Authored, Negotiated

## Using AI
Harvard's guidance: use AI to brainstorm, tighten, or add job-description keywords, but the person must
remain the author and the result must authentically represent them (AI alone tends to be generic).

## Harness rules layered on top **(harness addition)**
- **Never add facts.** Style edits may reword; they may not add employers, titles, dates, tools, or numbers
  that are not in `main/main.yaml` (see AGENTS.md).
- **One bullet = verb + what you did + result/scale**, one to two lines. Lead with the result when it is the strongest part.
- **Plain-English test:** could a recruiter with no engineering background tell why it matters? Translate jargon into
  an outcome ("used 5x less memory so more assistants fit on one server" only if that inference is in the source;
  otherwise state just the measured comparison).
- **Numbers need provenance.** Quote only figures present in `main/main.yaml` or a cited source, with the comparison
  baseline ("vs. seven competing tools"), and keep scope honest (pilot, single task, etc.).
- Prefer 3-5 bullets for the most relevant role, 1-3 for older or less relevant ones. Aim for one page.
- Visual layout (page fill, bold keywords, spacing, skills groups) is the `resume-layout` skill; the template and
  `hj build` own fonts and spacing, so never adjust those by hand.
