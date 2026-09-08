---
description: Revise an existing feature's plan/PR breakdown for changed requirements, creating a new numbered version.
argument-hint: <feature-name> <what's changing>
---

# Update Feature

Revise an existing `.features/<slug>/` spec in response to changed requirements. This always produces a new version — it never edits an existing version's files in place.

## Process

1. Parse `<feature-name>` and the description of what's changing from `$ARGUMENTS`. If `.features/<slug>/` doesn't exist, tell the user to use `/add-feature` instead and stop.
2. Read `meta.json` to find `current_version = V`, then read `plan/v{V}.md`, every file in `pr/v{V}/`, and the `prs` status map (which PRs at this version are already `implemented`).
3. Work out what needs to change:
   - Draft an updated top-level plan reflecting the new requirements.
   - Draft an updated PR breakdown: leave already-`implemented` PRs' scope alone — don't ask the user to redo shipped work. If new requirements affect an implemented PR's original intent, note the delta as a follow-up concern (e.g. a new PR) rather than rewriting history. Add/remove/resplit only the still-`pending` PRs as needed, by separation of concerns.
4. Always show the user a summary of what's changing (plan diff + PR-list diff) and iterate until they explicitly approve — do not write files until they've signed off.
5. Once approved, write a full new snapshot (never patch old versions):
   - `plan/v{V+1}.md`
   - `pr/v{V+1}/NN-<pr-slug>.md` for every PR in the new breakdown — carry forward unchanged PR files verbatim, renumber if ordering changed.
   - Update `meta.json`:
     - `current_version = V+1`
     - append to `versions`: `{"version": V+1, "date": "<ISO date>", "summary": "<why this changed>"}`
     - carry forward `prs` status for every PR whose scope didn't materially change; mark newly added/resplit PRs `"pending"`.
6. Commit the new version's files and `meta.json` on the current branch, message: `Update feature plan: <name> (v{V+1})`. Do not push.
7. Report what changed, the new version number, and that `/implement-feature` will now work from v{V+1}.

## Rules

- Never overwrite `plan/v{V}.md` or `pr/v{V}/` — always write the next version number.
- Don't silently redefine PRs that are already `implemented`; flag scope drift instead of rewriting their history.
- If "changing requirements" is vague, ask what's actually changing before drafting anything.
