#!/usr/bin/env bash
# profile-stats-update.sh — nightly refresh of the GitHub profile README.
#
# Runs on this machine, not GitHub Actions: scheduled runs there queue behind
# throttled Actions and get cut off, so the profile silently went stale.
# Driven by ~/Library/LaunchAgents/com.jemanuel.profile-stats.plist (05:00)
# through ~/.local/bin/profile-stats-update.sh, the launcher in this directory,
# which runs a snapshot of this file: the run does a `git pull`, and bash must
# not keep reading a script that the pull has rewritten. Install:
#   cp ops/profile-stats-launcher.sh ~/.local/bin/profile-stats-update.sh
#   cp ops/com.jemanuel.profile-stats.plist ~/Library/LaunchAgents/
#   launchctl bootstrap "gui/$(id -u)" ~/Library/LaunchAgents/com.jemanuel.profile-stats.plist
#
# Stage 1 (every night, deterministic): bash update-stats.sh refreshes stats,
# Building Now, star history, writing and Live Demos previews, then commits
# and pushes the generated files.
#
# Stage 2 (only when there is work, Claude Code headless): runs when a public
# repository is neither on the profile nor deliberately excluded
# (scripts/profile_coverage.py), when an exclusion's revisit date arrives, or
# when stage 1 failed or logged a problem it cannot fix itself (a stale
# Building Now section, a failed star chart, a broken Live Demos preview).
# Instructions: scripts/nightly_curation_prompt.md. Transcript:
# ~/.local/share/profile-stats/curation-YYYY-MM-DD.log.
#
# Manual run: bash ~/.local/bin/profile-stats-update.sh
#             bash ~/.local/bin/profile-stats-update.sh --dry-run
#             (no commit, no push, no Claude; logs what stage 2 would do)
#
# Every generated file this run leaves modified is restored to HEAD on exit.
# The run refuses to start when those files are dirty, so leaving them
# modified would block every later scheduled run until someone cleaned up.

export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

REPO="$HOME/projects/Dicklesworthstone"
LOG_DIR="$HOME/.local/share/profile-stats"
LOG="$LOG_DIR/update.log"
CURATION_LOG="$LOG_DIR/curation-$(date +%Y-%m-%d).log"
CURATION_TIMEOUT=7200
TRACKED=(README.md stats.svg stats-light.svg languages.svg languages-light.svg
         star_history.svg star_history-light.svg)

DRY_RUN=0
[ "${1:-}" = "--dry-run" ] && DRY_RUN=1

log() { printf '%s  %s\n' "$(date '+%Y-%m-%d %H:%M:%S %Z')" "$*" >> "$LOG"; }
die() { log "FAIL: $*"; exit 1; }

mkdir -p "$LOG_DIR"
log "=== run start (dry_run=$DRY_RUN) ==="

# Optional overrides, e.g. X_FOLLOWERS_LABEL=48.7K — lets the X follower count
# be bumped without editing update-stats.sh in the repo.
if [ -f "$HOME/.config/profile-stats.env" ]; then
  # shellcheck disable=SC1091
  . "$HOME/.config/profile-stats.env"
  log "sourced ~/.config/profile-stats.env"
fi

# Don't collide with a manual run (launchd already serializes against itself).
if pgrep -qf 'update-stats\.sh' 2>/dev/null; then
  log "SKIP: update-stats.sh already running"
  exit 0
fi

cd "$REPO" || die "cannot cd to $REPO"

for bin in gh jq python3 git curl claude timeout; do
  command -v "$bin" >/dev/null 2>&1 || die "missing dependency: $bin"
done

# Offline or locked keychain: bail cleanly and try again tomorrow.
gh auth status >/dev/null 2>&1 || die "gh not authenticated (keychain locked or offline?)"

if [ -n "$(git status --porcelain -- "${TRACKED[@]}")" ]; then
  die "generated profile files were already dirty; refusing to overwrite them"
fi
if ! git diff --cached --quiet; then
  die "the repository already has staged changes; refusing to include them"
fi

# The generated files were clean at the check above, so anything still
# modified when this script exits was written by this run and never committed.
# shellcheck disable=SC2329  # invoked directly and by the EXIT trap
restore_generated() {
  if [ -n "$(git status --porcelain -- "${TRACKED[@]}")" ]; then
    if git checkout -q HEAD -- "${TRACKED[@]}" 2>>"$LOG"; then
      log "restored uncommitted generated files to HEAD"
    else
      log "WARN: could not restore generated files; the next run will refuse until they are clean"
    fi
  fi
}
trap restore_generated EXIT

# A rebase that stops on a conflict would leave the repository mid-rebase and
# block every later run, so back out of it and carry on with local state.
pull_rebase() {
  git pull --rebase --quiet 2>>"$LOG" && return 0
  if [ -d "$(git rev-parse --git-path rebase-merge)" ] || [ -d "$(git rev-parse --git-path rebase-apply)" ]; then
    git rebase --abort 2>>"$LOG" && log "aborted the stopped rebase"
  fi
  return 1
}

push_with_retries() {
  local attempt
  for attempt in 1 2 3; do
    if git push --quiet 2>>"$LOG"; then
      log "pushed on attempt $attempt"
      return 0
    fi
    log "WARN: push attempt $attempt failed; rebasing and retrying"
    pull_rebase || log "WARN: rebase during retry failed"
    sleep $((attempt * 10))
  done
  return 1
}

pull_rebase || log "WARN: git pull --rebase failed; continuing on local state"

# ── Stage 1: deterministic refresh ────────────────────────────────────────
RUN_OUTPUT=$(mktemp "$LOG_DIR/.run.XXXXXX")
trap 'rm -f "$RUN_OUTPUT"; restore_generated' EXIT

log "running update-stats.sh"
STAGE1_OK=1
bash update-stats.sh >"$RUN_OUTPUT" 2>&1 || STAGE1_OK=0
cat "$RUN_OUTPUT" >> "$LOG"

if [ "$STAGE1_OK" -eq 0 ]; then
  log "FAIL: update-stats.sh exited non-zero; handing it to the curation stage"
  restore_generated
elif git diff --quiet -- "${TRACKED[@]}"; then
  log "no generated changes to commit"
else
  log "changed: $(git diff --name-only -- "${TRACKED[@]}" | tr '\n' ' ')"
  if [ "$DRY_RUN" -eq 0 ]; then
    git add -- "${TRACKED[@]}" || die "git add failed"
    git commit --only --quiet -m "Update GitHub stats ($(date +%Y-%m-%d))" \
      -- "${TRACKED[@]}" >>"$LOG" 2>&1 \
      || die "git commit failed"
    push_with_retries || die "push failed after 3 attempts (commit is local, will retry next run)"
  fi
fi

# ── Stage 2: Claude Code curation, only when there is work ───────────────
TASKS=""

if COVERAGE=$(gh repo list Dicklesworthstone --limit 1000 --visibility public \
      --json name,description,isArchived,isEmpty,isFork,stargazerCount,createdAt,pushedAt \
      | python3 scripts/profile_coverage.py 2>>"$LOG"); then
  if [ "$(printf '%s' "$COVERAGE" | jq 'length')" != "0" ]; then
    TASKS+=$'### Repositories that need a profile decision\n\n```json\n'"$COVERAGE"$'\n```\n\n'
  fi
else
  log "WARN: coverage check failed; skipping repository curation tonight"
fi

if [ "$STAGE1_OK" -eq 0 ]; then
  TASKS+=$'### Failed refresh\n\n`bash update-stats.sh` exited non-zero. The end of its output:\n\n```\n'"$(tail -n 60 "$RUN_OUTPUT")"$'\n```\n\n'
fi
PROBLEMS=$(grep -nE 'preserving the existing Building Now section|star history generation failed|Live Demos preview .* does not serve an image|^error: ' "$RUN_OUTPUT" 2>/dev/null || true)
if [ -n "$PROBLEMS" ]; then
  TASKS+=$'### Problems the refresh logged but could not fix itself\n\n```\n'"$PROBLEMS"$'\n```\n\nThe full run output is in ~/.local/share/profile-stats/update.log (the last run).\n\n'
fi

if [ -z "$TASKS" ]; then
  log "curation: nothing to do"
  log "=== run end ==="
  exit 0
fi

if [ "$DRY_RUN" -eq 1 ]; then
  log "curation would run (dry run, skipped). Tonight's work:"
  printf '%s\n' "$TASKS" >> "$LOG"
  log "=== run end (dry-run, nothing committed) ==="
  exit 0
fi

PROMPT="$(cat scripts/nightly_curation_prompt.md)

## Tonight's work

$TASKS"

log "curation: starting Claude Code (transcript: $CURATION_LOG)"
{
  printf '=== %s ===\n' "$(date '+%Y-%m-%d %H:%M:%S %Z')"
  printf '%s\n\n--- output ---\n' "$TASKS"
} >> "$CURATION_LOG"
CURATION_STATUS=0
# Opus, not the headless default: these runs are rare and may write public
# profile prose.
timeout "$CURATION_TIMEOUT" claude -p "$PROMPT" --model opus \
  --dangerously-skip-permissions --no-session-persistence \
  >>"$CURATION_LOG" 2>&1 || CURATION_STATUS=$?
log "curation: Claude Code exited $CURATION_STATUS"

LEFTOVER=$(git status --porcelain --untracked-files=no | grep -vE ' (README\.md|[a-z_-]+\.svg)$' || true)
if [ -n "$LEFTOVER" ]; then
  log "WARN: curation left uncommitted changes; the next run will start on top of them:"
  printf '%s\n' "$LEFTOVER" >> "$LOG"
fi
if [ "$(git rev-list --count '@{u}..HEAD' 2>/dev/null || echo 0)" != "0" ]; then
  log "WARN: local commits are not pushed yet; trying once more"
  push_with_retries || log "WARN: push still failing; the next run will retry"
fi

log "=== run end ==="
