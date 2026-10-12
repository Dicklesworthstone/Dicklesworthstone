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
  days, using both default-branch commit count and the aggregate
  additions/deletions between the default branch's first-parent state at the
  window boundary and its current tip.
  Never rank that section by `pushedAt` or `updatedAt` alone. Show the raw
  activity totals in the README so readers can audit the ranking. The current
  implementation fetches current GitHub default branches, then measures one
  fixed time window through `scripts/recent_activity.py`; never measure
  potentially stale local refs. When measurement fails, the run still succeeds
  and keeps the old section, so check `~/.local/share/profile-stats/update.log`
  for "preserving the existing Building Now section" (it froze from Sep 10 to
  Sep 24, 2026 when too many recent repos were not cloned locally). The
  section's caption carries its window's end date, so a frozen table also
  shows its age on the page.
- List only projects and sites backed by a public GitHub repository. A live
  domain on Vercel or Cloudflare may still be unannounced; without a public
  repo, leave it off every section. Re-check sites already on the page too:
  smearedlife.com stayed listed with a private repo until Oct 12, 2026. Before
  calling a site repo-less, search the live page's title or a distinctive
  string with `gh search code --owner Dicklesworthstone` and check the hit's
  visibility (the search includes private repos): eidetic-engine.org is built
  from the public `eidetic-engine-website-project`, whose name matches no
  domain.
- Verify every Live Demos preview with `curl -w '%{content_type}'`, not just
  the status code: a site that drops its OG image can still return 200 HTML.
  Each run of `scripts/update_readme.py` repeats that check for every card: it
  replaces a preview that no longer serves an image with the site's current
  same-site HTTPS `og:image` when that one does, and otherwise only logs
  "Live Demos preview ... does not serve an image", so still check new cards
  by hand before publishing.
- Keep the star-history main panel at 14 repositories unless the profile
  layout is deliberately redesigned. Select the leading series from both total
  stars and 90-day growth, then regenerate both light and dark SVGs. The
  "Rising fast" panel below it (added Oct 12, 2026) charts up to 6 repos outside
  those 14 that gained at least 20 stars and grew at least 25% over 28 days, on
  their own axes so small counts stay visible. The thresholds and their
  data-based justification live in `scripts/star_history.py`; re-check them
  against the current distribution before changing either.
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
