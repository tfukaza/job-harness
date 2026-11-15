---
name: setup-profile
description: Interview the user once to fill main/profile.yaml (contact, work authorization, location and relocation, compensation, employers, optional demographics) so portal forms can be pre-filled. Use at first setup, when profile.yaml is missing or has blank fields, or when the user's circumstances change.
---

# Set up the profile

Goal: collect the answers that application portals ask over and over, and save them to `main/profile.yaml`
(gitignored, never sent anywhere) so `hj apply` can pre-fill forms. Schema and placeholders: `main/profile.example.yaml`.

## Rules
- **Never guess or infer personal facts.** Only write what the user states or what is already in their files.
- **Pre-fill, then ask only what is missing.** Read `main/profile.yaml` if it exists and `main/main.yaml`
  (name, links, employers from `experience`). Show what you already know and ask the user to confirm or correct it.
- **Batch the questions** (one group at a time, a few questions per message; use your agent's multiple-choice
  question tool if it has one, otherwise plain chat). Do not ask 20 questions at once.
- **Everything sensitive is optional.** For demographics and date of birth, say each is voluntary and that
  "skip" leaves it blank. Blank means the apply script will not fill it (forms usually offer "decline to answer").
- **Date of birth** is only for the rare form that explicitly asks. Never put it, or age, on a resume.
- Before writing, **show a summary and get a yes.** Then write `main/profile.yaml`, keeping the example's keys.
- Do not commit the file. Do not paste its contents into other services.

## Questions, in order
1. **Identity and contact:** legal first and last name; preferred name; email; phone; LinkedIn; GitHub;
   personal website (or none); current city or region; pronouns (optional).
2. **Work eligibility:** work authorization (citizen, permanent resident, visa type) and the exact phrase they
   want on forms; whether they now or in the future need visa sponsorship; confirm they are 18 or older.
3. **Location and preferences:** willing to relocate? to where; remote, hybrid or in-office preference;
   acceptable office locations (these should also be reflected in `search/criteria.yaml`).
4. **Compensation and timing:** target salary or range (and currency); notice period or earliest start date.
5. **History:** previous employers (offer the ones found in `main/main.yaml`), for "have you worked here before?";
   default answer for "how did you hear about us?" (the apply step can override it per posting from the job source).
6. **Optional voluntary self-identification (US EEO):** gender, Hispanic/Latino, race/ethnicity, disability,
   veteran status, sexual orientation. Remind them each can be skipped.
7. **Optional:** date of birth (only if they want it stored).

## Finish
- Save the file, then list any fields still blank so the user knows what forms will leave for them.
- Suggest next steps: fill `main/main.yaml` if it is empty (see `main/main.example.yaml` when available), then run `find-jobs`.
