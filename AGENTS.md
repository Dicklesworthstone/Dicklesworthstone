# Repository Instructions

## Purpose and generated surfaces

This repository renders Jeffrey Emanuel's GitHub profile. `README.md` is a
hybrid document: its portfolio prose is curated by hand, while delimited
sections, counters, badges, and SVG cards are refreshed by `update-stats.sh`,
`scripts/update_readme.py`, and `scripts/star_history.py`.

Before changing the profile, read this file and all of `README.md`. Read each
generator completely before changing its output contract. Do not hand-edit
content between `BEGIN AUTO-*` and `END AUTO-*` markers; change its generator
and regenerate it.

## Rules for every profile refresh

- Use live GitHub data for repository metadata and public statistics. Keep
  claims about project readiness and capabilities honest to each project's
  current README and implementation.
- Build "What I'm Building Now" from actual Git activity over the trailing 14
  days, using both unique default-branch commit count and additions/deletions.
  Never rank that section by `pushedAt` or `updatedAt` alone. Show the raw
  activity totals in the README so readers can audit the ranking. The current
  implementation uses local clones under `~/projects` and
  `scripts/recent_activity.py`.
- Keep the star-history chart at 14 repositories unless the profile layout is
  deliberately redesigned. Select the leading series from both total stars
  and recent growth, then regenerate both light and dark SVGs.
- When Jeffrey supplies a new X follower count, update both the generated badge
  for the current run and the `X_FOLLOWERS_LABEL` fallback in
  `update-stats.sh`.
- Treat `.ee/`, `.wrangler/`, build output, caches, and unrelated worktree
  changes as out of scope. Never stage or alter them as part of a profile
  update.

## Refresh and verification

Run `bash update-stats.sh` from the repository root. Before publishing, run:

```bash
bash -n update-stats.sh
python3 -m py_compile scripts/update_readme.py scripts/recent_activity.py scripts/star_history.py
xmllint --noout stats.svg stats-light.svg languages.svg languages-light.svg star_history.svg star_history-light.svg
git diff --check
```

Inspect the rendered Markdown tables and both star-history themes after every
regeneration. Stage only the intended profile sources and generated assets.
