# job-harness

A human-in-the-loop job application harness, built to be driven by a coding agent (Claude Code, Codex, ...).
Keep one big "main" resume; the agent finds jobs, tailors a PDF per posting, and fills the application form.
**You approve every step and press Submit yourself.**

## Start
```bash
git clone https://github.com/tfukaza/job-harness && cd job-harness
```
Open the folder in your coding agent and say: **"set up the harness"**. Then **"find me jobs"**.

Everything the agent needs (rules, setup steps, workflow, commands) is in [AGENTS.md](AGENTS.md).
Personal data stays on your machine; it is gitignored.

## Credits
`resume-style` paraphrases the [Harvard College Guide to Creating a Strong Resume](https://careerservices.fas.harvard.edu/resources/create-a-strong-resume/)
(Harvard FAS Mignone Center for Career Success; not endorsed by Harvard). YC discovery uses the
[yc-oss](https://github.com/yc-oss/api) dataset.
