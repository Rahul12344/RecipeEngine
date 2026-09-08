---
description: Create a new versioned feature spec under .features/<slug>/ — top-level plan + PR breakdown, split by separation of concerns.
argument-hint: <feature-name> <description>
---

# Add Feature

Create a new versioned feature spec under `.features/`.

## Input

`$ARGUMENTS` — a feature name followed by a description. If either is missing, or the description is too vague to plan from, ask the user before doing anything else. Don't guess at scope.

## Layout you must produce

```
.features/<slug>/
  meta.json
  plan/v1.md
  pr/v1/01-<pr-slug>.md
  pr/v1/02-<pr-slug>.md
  ...
```

- `<slug>`: kebab-case of the feature name.
- If `.features/<slug>/` already exists, STOP and tell the user to run `/update-feature` instead — do not overwrite an existing feature.

## Process

1. Slugify the feature name and check for an existing folder (abort per above if found).
2. Skim the repo (README, relevant source directories) enough to ground the plan in how this codebase actually works — don't invent architecture that's checkable by reading.
3. Draft, in your reply, **not yet written to disk**:
   - **Top-level plan**: what the feature is asking for, goals, explicit non-goals, key design/architecture decisions, and open questions.
   - **PR breakdown**: split the plan into PRs by separation of concerns (e.g. data layer vs. API vs. UI vs. tests/docs — whatever concerns actually apply here, not a fixed template). Each PR gets a sequence number starting at `01`, a title, its scope, the files/areas it likely touches, its dependencies on earlier PRs in the list, and acceptance criteria.
4. Always show this draft to the user and iterate until they explicitly approve it — do not write any files until they've signed off, even if their initial description already seems complete enough to propose a full split in one shot.
5. Once approved, write the artifacts:
   - `plan/v1.md` — the approved top-level plan.
   - `pr/v1/NN-<pr-slug>.md` — one file per PR, numbered `01`, `02`, ... in landing order, each containing title / scope / touches / dependencies / acceptance criteria.
   - `meta.json`:
     ```json
     {
       "name": "<feature name>",
       "slug": "<slug>",
       "description": "<original description>",
       "created_at": "<ISO date>",
       "current_version": 1,
       "versions": [
         {"version": 1, "date": "<ISO date>", "summary": "Initial plan"}
       ],
       "prs": {
         "01": {"slug": "<pr-slug>", "title": "<pr title>", "status": "pending"},
         "02": {"slug": "<pr-slug>", "title": "<pr title>", "status": "pending"}
       }
     }
     ```
6. Stage and commit only the new `.features/<slug>/` files on the current branch, message: `Add feature plan: <name> (v1)`. Do not push. Do not touch unrelated files.
7. Report the path written, the PR count, and the next step (`/implement-feature <slug>`).

## Rules

- Never invent requirements the user didn't state or approve — ask instead.
- Keep the plan and PR docs concrete and specific to this codebase; no generic boilerplate.
- Don't write anything under `.features/` that the user hasn't approved.
