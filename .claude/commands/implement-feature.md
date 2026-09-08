---
description: Implement the next (or a specified) PR from a feature's latest plan version, and open a draft PR for it.
argument-hint: <feature-name> [pr-number|all]
---

# Implement Feature

Implement one or more PR-slices from an existing `.features/<slug>/` spec, working strictly from its **latest plan version**, and open a real draft GitHub PR for each.

## Resolve input

1. Parse `$ARGUMENTS` for `<feature-name>` and optionally a PR number (e.g. `02`) or `all`. If the feature name is missing or `.features/<slug>/` doesn't exist, list the features under `.features/` and ask.
2. Read `.features/<slug>/meta.json`. Let `V = current_version`. Always implement from `plan/v{V}.md` / `pr/v{V}/` — never an older version, even if one exists on disk.
3. Read `plan/v{V}.md` for context, every file in `pr/v{V}/` for the PR breakdown, and `meta.json.prs` for each PR's status (`pending` / `implemented`) at this version.
4. Determine target PR(s):
   - explicit number given → that one (if already `implemented`, confirm with the user before redoing it)
   - `all` → every `pending` PR, in dependency order
   - nothing given → the lowest-numbered `pending` PR
5. If a target PR depends on a PR that isn't yet `implemented`, implement the dependency first — or, if reordering seems unsafe (e.g. the dependency's scope is itself unclear), stop and ask rather than guessing.

## For each target PR, in order

1. Base branch: `main` if the PR has no unimplemented dependency, otherwise the branch of its most recently implemented dependency.
2. Create/checkout `feature/<slug>-pr-{NN}-<pr-slug>` off that base.
3. Implement exactly what that PR file scopes — nothing from other PRs in the plan. Follow this repo's existing conventions.
4. Run whatever build/test/lint commands apply to the touched areas; fix failures before proceeding.
5. Commit, with a message summarizing the PR's title.
6. Push the branch and run `gh pr create --draft` against the base branch determined in step 1, with:
   - title = the PR file's title
   - body = its scope + acceptance criteria, plus a link back to `.features/<slug>/pr/v{V}/NN-<pr-slug>.md`
7. Note the resulting branch name and PR URL for the metadata update below (don't write it yet).

## After all target PRs are handled

1. Switch back to the branch that was checked out when this command was invoked.
2. Update `.features/<slug>/meta.json`: for each PR just implemented, set `status: "implemented"`, `branch`, and `pr_url`.
3. Commit this metadata update on that original branch, message: `Update feature metadata: <name> (PR <NN[, NN...]> implemented)`. Do not push it automatically — mention to the user it's a local commit they can push.
4. Report the branch name and PR URL for each implemented PR.

## Rules

- Never implement from a stale plan version — always resolve `current_version` fresh from `meta.json` first, every run.
- Never bundle more than one PR-slice's changes into a single branch/PR.
- If a PR file's scope is ambiguous or missing information needed to implement it, stop and ask rather than guessing.
