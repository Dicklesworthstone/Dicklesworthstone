# Nightly profile curation

You are running unattended, overnight, in Jeffrey Emanuel's GitHub profile
repository (the current directory). Nobody will answer questions. Decide and
act within these rules, then stop.

1. Read `AGENTS.md` and `README.md` completely first. They are binding,
   especially the rules on public repositories, honest claims, and the
   verification checklist.
2. Do only the work listed under "Tonight's work" below.
3. **Repositories that need a profile decision.** For each one, read its
   GitHub README (`gh api repos/Dicklesworthstone/NAME/readme -H 'Accept:
   application/vnd.github.raw'`), and check its visibility and activity.
   - If it is a real, fleshed-out project, add one row to the README section
     where similar projects live. Copy that section's row format exactly,
     including a star badge with `&repo=Dicklesworthstone%2FNAME`. Write one
     honest line drawn from the project's own README, with no superlatives and
     no capability it does not have yet. A site repository named after its
     domain goes where the other sites are; add a Live Demos card only if
     `curl -sL -o /dev/null -w '%{content_type}'` on its `og:image` returns
     `image/*`.
   - Otherwise, add it to `scripts/profile_exclusions.json` with a one-line
     reason. Include `"revisit": "YYYY-MM-DD"`, 30 days out, if it could become
     ready later.
   - An entry marked `previousExclusion` was skipped before. Re-check it, then
     either list it or update its reason and revisit date.
   - When unsure, leave it off and record the exclusion with a revisit date.
4. **Failed or stale refresh.** Read the log excerpt, find the root cause, and
   fix it in the generator code with a regression test if it is a bug. A
   transient network failure needs no code change. Then run
   `bash update-stats.sh`. For a Live Demos preview that does not serve an
   image, re-check the site first. If the site does not respond, change
   nothing: it may be back tomorrow. If it is up but its preview moved, point
   the card at its current `og:image` once that serves `image/*`. For "Building
   Now shows withheld repo NAME", add NAME to `RECENT_DESCRIPTION_OVERRIDES` in
   `scripts/update_readme.py` with one line that states only what its code
   does today, per its README's own status section; if it is ready to list
   instead, list it as in rule 3 and drop its exclusion.
5. Verify with the `AGENTS.md` checklist and
   `python3 -m unittest tests.test_profile_generators`. Nothing may be
   committed while either fails.
6. Commit only the files you changed, by path
   (`git commit --only -- <paths>`), with a message that says what and why,
   then `git pull --rebase` and `git push`. Never force-push, delete files,
   rewrite history, or touch `.ee/`, token exports, or anything outside this
   repository. Leave `README.md` and the six SVGs committed and clean.
7. Finish with a short plain-text summary of every change and decision.
