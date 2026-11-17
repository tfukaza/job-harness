# job-harness

A human-in-the-loop job application harness, built to be driven by a coding agent (Claude Code, Codex, ...).
**By default you approve every step and press Submit yourself.**

## Setup
1. `git clone https://github.com/tfukaza/job-harness && cd job-harness`
2. Open the folder in your coding agent and say **"set up the harness"**.

## What it can do
- **Find jobs** from company job boards (Greenhouse, Lever, Ashby) and hiring YC startups, filtered by title,
  location and the years of experience each posting really asks for.
- **Learn your taste** from every like and dislike, and research each company (what it does, stage, estimated pay).
- **Tailor a one-page resume** per job from your main resume, without inventing anything, rendered to PDF.
- **Write form answers** in your own voice, checked by a panel of reviewer agents.
- **Fill application forms** in your own browser, then stop for you to submit.
- **Track applications** and read job email (read-only) for replies and interview invites.

## Workflow
1. **Find:** say "find me jobs". Like or dislike each job and say why; the next round learns from it.
2. **Tailor:** pick a job. The agent researches the company and drafts a resume; you edit and approve it.
3. **Apply:** the agent fills the form and attaches the PDF. You review and press Submit.
4. **Track:** the tracker and your inbox follow each application from applied to offer.

## Resume samples
Pick a style with `base:` in `main/resume-style.yaml`. Click a picture for the PDF (the sample person is fictional).

| `traditional` (default) | `rails` | `classic` |
|---|---|---|
| [![traditional](docs/samples/traditional.png)](docs/samples/traditional.pdf) | [![rails](docs/samples/rails.png)](docs/samples/rails.pdf) | [![classic](docs/samples/classic.png)](docs/samples/classic.pdf) |

## Details
- Setup installs what's missing (asking first), turns your resume into `main/main.yaml`, interviews you for your
  profile, and sets your search criteria.
- Your personal files (resume, profile, jobs, tracker, search results) are gitignored and stay on your machine.
- How much the agent does on its own is set in `main/mode.yaml`: `review` (default, you approve everything),
  `assist` or `yolo`.
- Rules, commands and every option for agents: [AGENTS.md](AGENTS.md).

## Credits
`resume-style` paraphrases the [Harvard College Guide to Creating a Strong Resume](https://careerservices.fas.harvard.edu/resources/create-a-strong-resume/)
(Harvard FAS Mignone Center for Career Success; not endorsed by Harvard). YC discovery uses the
[yc-oss](https://github.com/yc-oss/api) dataset.
