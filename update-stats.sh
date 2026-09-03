#!/usr/bin/env bash
set -euo pipefail

# update-stats.sh — Fetches live GitHub stats and refreshes profile artifacts.
# Used by the local daily updater and the manual GitHub Actions fallback.
# Requires: gh CLI authenticated, jq, python3, curl

USERNAME="Dicklesworthstone"
MONTH=$(date +"%b %Y")

fmt() { python3 -c 'import sys; print(f"{int(sys.argv[1]):,}")' "$1"; }
calc_pct() {
  python3 -c 'import sys; den=int(sys.argv[2]); print("0.0" if den == 0 else f"{int(sys.argv[1]) * 100 / den:.1f}")' "$1" "$2"
}
bar_width() {
  python3 -c 'import sys; print(max(2, int(float(sys.argv[1]) * int(sys.argv[2]) / 100)))' "$1" "$2"
}
human_bytes() {
  python3 -c 'import sys; n=int(sys.argv[1]); print(f"{n // 1000000000}G" if n >= 1000000000 else (f"{n // 1000000}M" if n >= 1000000 else (f"{n // 1000}K" if n >= 1000 else f"{n}B")))' "$1"
}
xml_escape() {
  python3 -c 'import html, sys; print(html.escape(sys.argv[1], quote=True), end="")' "$1"
}
sanitize_color() {
  if [[ "$1" =~ ^#[0-9A-Fa-f]{6}$ ]]; then
    printf '%s' "$1"
  else
    printf '#888888'
  fi
}
require_integer_at_least() {
  local label="$1" value="$2" minimum="$3"
  if ! [[ "$value" =~ ^[0-9]+$ ]] || (( 10#$value < minimum )); then
    echo "GitHub returned an invalid ${label}: ${value:-<empty>}" >&2
    exit 1
  fi
}
gh_api() {
  local attempt result
  for attempt in 1 2 3; do
    if result=$(gh api "$@"); then
      printf '%s' "$result"
      return 0
    fi
    echo "  GitHub API attempt $attempt failed" >&2
    [ "$attempt" -lt 3 ] && sleep $((attempt * 2))
  done
  return 1
}
fetch_public_commit_count() {
  local attempt result count
  for attempt in 1 2 3; do
    if result=$(gh_api -X GET search/commits -f q="$COMMITS_SEARCH_QUERY" -f per_page=1); then
      count=$(printf '%s' "$result" | jq -r '
        if (.incomplete_results == false)
          and ((.total_count | type) == "number")
          and (.total_count > 0)
        then .total_count else empty end
      ')
      if [[ "$count" =~ ^[0-9]+$ ]]; then
        printf '%s' "$count"
        return 0
      fi
    fi
    echo "  Commit search attempt $attempt returned incomplete or invalid data" >&2
    [ "$attempt" -lt 3 ] && sleep 2
  done
  return 1
}
write_atomically() {
  local target="$1"
  local directory basename temporary
  directory=$(dirname "$target")
  basename=$(basename "$target")
  temporary=$(mktemp "${directory}/.${basename}.XXXXXX")
  if ! { cat > "$temporary" && chmod 0644 "$temporary" && mv -f -- "$temporary" "$target"; }; then
    rm -f -- "$temporary"
    return 1
  fi
}

echo "=== Fetching user profile ==="
PROFILE=$(gh_api "users/${USERNAME}")
FOLLOWERS=$(echo "$PROFILE" | jq -r '.followers')
FOLLOWING=$(echo "$PROFILE" | jq -r '.following')
PUBLIC_REPOS=$(echo "$PROFILE" | jq -r '.public_repos')

echo "=== Fetching public non-fork project count ==="
# shellcheck disable=SC2016
OPEN_SOURCE_PROJECTS=$(gh_api graphql -f login="$USERNAME" -f query='query($login: String!) {
  user(login: $login) {
    repositories(ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC) {
      totalCount
    }
  }
}' | jq -r '.data.user.repositories.totalCount')

echo "=== Fetching total public stars (paginated) ==="
TOTAL_STARS=0
CURSOR=""
PAGE=1
# shellcheck disable=SC2016
STARS_QUERY='query($login: String!, $after: String) {
  user(login: $login) {
    repositories(first: 100, after: $after, ownerAffiliations: OWNER, privacy: PUBLIC) {
      totalCount
      nodes { stargazerCount }
      pageInfo { endCursor hasNextPage }
    }
  }
}'
STAR_REPO_COUNT=0
EXPECTED_STAR_REPOS=""
while true; do
  if [ -z "$CURSOR" ]; then
    RESULT=$(gh_api graphql -f query="$STARS_QUERY" -f login="$USERNAME")
  else
    RESULT=$(gh_api graphql -f query="$STARS_QUERY" -f login="$USERNAME" -f after="$CURSOR")
  fi
  PAGE_STARS=$(printf '%s' "$RESULT" | jq -er '
    .data.user.repositories.nodes as $nodes
    | if (($nodes | type) == "array")
      and all($nodes[];
        ((.stargazerCount | type) == "number")
        and (.stargazerCount >= 0)
        and (.stargazerCount == (.stargazerCount | floor)))
      then [$nodes[].stargazerCount] | add // 0
      else error("invalid repository star metadata") end
  ')
  PAGE_STAR_REPOS=$(printf '%s' "$RESULT" | jq -er '.data.user.repositories.nodes | length')
  PAGE_TOTAL_REPOS=$(printf '%s' "$RESULT" | jq -er '
    .data.user.repositories.totalCount
    | if (type == "number") and (. >= 0) and (. == floor)
      then . else error("invalid totalCount") end
  ')
  if [ -z "$EXPECTED_STAR_REPOS" ]; then
    EXPECTED_STAR_REPOS="$PAGE_TOTAL_REPOS"
  elif (( 10#$PAGE_TOTAL_REPOS != 10#$EXPECTED_STAR_REPOS )); then
    echo "GitHub repository count changed during star pagination" >&2
    exit 1
  fi
  STAR_REPO_COUNT=$((STAR_REPO_COUNT + PAGE_STAR_REPOS))
  TOTAL_STARS=$((TOTAL_STARS + PAGE_STARS))
  echo "  Page $PAGE: +$PAGE_STARS stars (total: $TOTAL_STARS)"
  HAS_NEXT=$(echo "$RESULT" | jq -r '.data.user.repositories.pageInfo.hasNextPage | if type == "boolean" then tostring else error("invalid hasNextPage") end')
  [ "$HAS_NEXT" != "true" ] && break
  NEXT_CURSOR=$(echo "$RESULT" | jq -r '.data.user.repositories.pageInfo.endCursor | if type == "string" then . else error("invalid endCursor") end')
  if [ -z "$NEXT_CURSOR" ] || [ "$NEXT_CURSOR" = "$CURSOR" ]; then
    echo "GitHub returned an invalid repository pagination cursor" >&2
    exit 1
  fi
  CURSOR="$NEXT_CURSOR"
  PAGE=$((PAGE + 1))
done
if (( 10#$EXPECTED_STAR_REPOS != 10#$PUBLIC_REPOS || STAR_REPO_COUNT != 10#$EXPECTED_STAR_REPOS )); then
  echo "GitHub returned incomplete repository star metadata: expected ${PUBLIC_REPOS}, received ${STAR_REPO_COUNT}" >&2
  exit 1
fi

echo "=== Fetching contributions ==="
# shellcheck disable=SC2016
CONTRIB=$(gh_api graphql -f query='query($login: String!) { user(login: $login) { contributionsCollection { contributionCalendar { totalContributions } } } }' -f login="$USERNAME")
CONTRIBUTIONS=$(echo "$CONTRIB" | jq -r '.data.user.contributionsCollection.contributionCalendar.totalContributions')
CONTRIBUTIONS=${CONTRIBUTIONS_OVERRIDE:-$CONTRIBUTIONS}
README_CONTRIBUTIONS_RAW=$CONTRIBUTIONS

echo "=== Fetching public commits ==="
COMMITS_SEARCH_QUERY="${COMMITS_SEARCH_QUERY:-author:${USERNAME} is:public}"
if ! TOTAL_COMMITS=$(fetch_public_commit_count); then
  echo "GitHub commit search did not return a complete positive count; aborting refresh" >&2
  exit 1
fi

require_integer_at_least "star count" "$TOTAL_STARS" 1
require_integer_at_least "commit count" "$TOTAL_COMMITS" 1
require_integer_at_least "public repository count" "$PUBLIC_REPOS" 1
require_integer_at_least "open-source project count" "$OPEN_SOURCE_PROJECTS" 1
require_integer_at_least "follower count" "$FOLLOWERS" 1
require_integer_at_least "contribution count" "$CONTRIBUTIONS" 1
require_integer_at_least "following count" "$FOLLOWING" 0

echo ""
echo "Stars:         $(fmt $TOTAL_STARS)"
echo "Commits:       $(fmt "$TOTAL_COMMITS")"
echo "Public Repos:  $(fmt "$PUBLIC_REPOS")"
echo "Open Source:   $(fmt "$OPEN_SOURCE_PROJECTS")"
echo "Followers:     $(fmt "$FOLLOWERS")"
echo "Contributions: $(fmt "$CONTRIBUTIONS")"
echo "Following:     $(fmt "$FOLLOWING")"

STARS_FMT=$(fmt $TOTAL_STARS)
COMMITS_FMT=$(fmt "$TOTAL_COMMITS")
REPOS_FMT=$(fmt "$PUBLIC_REPOS")
FOLLOWERS_FMT=$(fmt "$FOLLOWERS")
CONTRIBUTIONS_FMT=$(fmt "$CONTRIBUTIONS")
README_CONTRIBUTIONS=$(fmt "$README_CONTRIBUTIONS_RAW")
FOLLOWING_FMT=$(fmt "$FOLLOWING")

README_STARS_LABEL="$(fmt $(( (TOTAL_STARS / 10) * 10 )))+"
README_FOLLOWERS_LABEL="$(fmt $(( (FOLLOWERS / 100) * 100 )))+"
X_FOLLOWERS_LABEL="${X_FOLLOWERS_LABEL:-48.7K}"
if ! [[ "$X_FOLLOWERS_LABEL" =~ ^([0-9]+|[0-9]{1,3}(,[0-9]{3})+)(\.[0-9]+)?[KkMm]?\+?$ ]]; then
  echo "Invalid X follower label: ${X_FOLLOWERS_LABEL:-<empty>}" >&2
  exit 1
fi

echo "=== Fetching Discord member count ==="
DISCORD_INVITE_CODE="${DISCORD_INVITE_CODE:-gnCHsYDR25}"
DISCORD_MEMBERS="${DISCORD_MEMBERS:-}"
if [ -z "$DISCORD_MEMBERS" ]; then
  if DISCORD_JSON=$(curl -fsSL "https://discord.com/api/v10/invites/${DISCORD_INVITE_CODE}?with_counts=true" 2>/dev/null); then
    if ! DISCORD_MEMBERS=$(printf '%s' "$DISCORD_JSON" | jq -er '
      .approximate_member_count
      | if (type == "number") and (. >= 0) and (. == floor)
        then tostring else error("invalid member count") end
    ' 2>/dev/null); then
      echo "Discord returned an invalid response; leaving the README fallback in place" >&2
      DISCORD_MEMBERS=""
    fi
  fi
fi
if [ -n "$DISCORD_MEMBERS" ] && ! [[ "$DISCORD_MEMBERS" =~ ^[0-9]+$ ]]; then
  echo "Discord returned an invalid member count; leaving the README fallback in place" >&2
  DISCORD_MEMBERS=""
fi
if [ -n "$DISCORD_MEMBERS" ]; then
  DISCORD_MEMBERS_FMT=$(fmt "$DISCORD_MEMBERS")
  export DISCORD_MEMBERS_FMT
  echo "Discord:      ${DISCORD_MEMBERS_FMT} members"
else
  echo "Discord:      count unavailable; leaving README fallback in place"
fi

RECENT_REPOS_JSON_CONTENT=$(gh repo list "$USERNAME" \
  --limit 1000 \
  --visibility public \
  --json name,description,primaryLanguage,defaultBranchRef,pushedAt,updatedAt,stargazerCount,isArchived,isFork,url)
RECENT_REPO_COUNT=$(printf '%s' "$RECENT_REPOS_JSON_CONTENT" | jq -r \
  'if type == "array" then length else error("repository metadata is not an array") end')
require_integer_at_least "public repository metadata count" "$RECENT_REPO_COUNT" 1
if (( 10#$RECENT_REPO_COUNT != 10#$PUBLIC_REPOS )); then
  echo "GitHub repository metadata was incomplete: expected ${PUBLIC_REPOS}, received ${RECENT_REPO_COUNT}" >&2
  exit 1
fi
export RECENT_REPOS_JSON_CONTENT
if RECENT_ACTIVITY_JSON_CONTENT=$(printf '%s' "$RECENT_REPOS_JSON_CONTENT" | python3 scripts/recent_activity.py); then
  export RECENT_ACTIVITY_JSON_CONTENT
else
  echo "Recent activity measurement unavailable; preserving the existing Building Now section"
fi
export OPEN_SOURCE_PROJECTS README_CONTRIBUTIONS README_STARS_LABEL README_FOLLOWERS_LABEL X_FOLLOWERS_LABEL

# ── Fetch language stats ──────────────────────────────────────────────
echo ""
echo "=== Fetching language stats (this takes a moment) ==="

declare -A LANG_BYTES
declare -A LANG_COLORS
TOTAL_LANG_REPOS=0
CURSOR=""
PAGE=1
# shellcheck disable=SC2016
LANG_QUERY='query($login: String!, $after: String) {
  user(login: $login) {
    repositories(first: 100, after: $after, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC) {
      totalCount
      nodes {
        languages(first: 100, orderBy: {field: SIZE, direction: DESC}) {
          totalCount
          edges { size node { name color } }
        }
      }
      pageInfo { endCursor hasNextPage }
    }
  }
}'
LANG_REPO_COUNT=0
EXPECTED_LANG_REPOS=""
while true; do
  if [ -z "$CURSOR" ]; then
    REPOS_JSON=$(gh_api graphql -f query="$LANG_QUERY" -f login="$USERNAME")
  else
    REPOS_JSON=$(gh_api graphql -f query="$LANG_QUERY" -f login="$USERNAME" -f after="$CURSOR")
  fi

  if ! printf '%s' "$REPOS_JSON" | jq -e '
    .data.user.repositories.nodes as $nodes
    | (($nodes | type) == "array")
      and all($nodes[];
        ((.languages | type) == "object")
        and ((.languages.totalCount | type) == "number")
        and (.languages.totalCount >= 0)
        and (.languages.totalCount == (.languages.totalCount | floor))
        and ((.languages.edges | type) == "array")
        and (.languages.totalCount == (.languages.edges | length))
        and all(.languages.edges[];
          ((.size | type) == "number")
          and (.size >= 0)
          and (.size == (.size | floor))
          and ((.node.name | type) == "string")
          and (.node.name != "")
          and ((.node.color == null) or ((.node.color | type) == "string"))))
  ' >/dev/null; then
    echo "GitHub returned invalid or incomplete language metadata" >&2
    exit 1
  fi
  if ! LANG_ROWS=$(printf '%s' "$REPOS_JSON" | jq -r '.data.user.repositories.nodes[].languages.edges[] | [.node.name, .size, (.node.color // "#888888")] | @tsv'); then
    echo "Could not decode GitHub language metadata" >&2
    exit 1
  fi

  # Aggregate language bytes and colors.
  while IFS=$'\t' read -r lang bytes color; do
    [ -z "$lang" ] && continue
    if ! [[ "$bytes" =~ ^[0-9]+$ ]]; then
      echo "GitHub returned an invalid language byte count" >&2
      exit 1
    fi
    LANG_BYTES[$lang]=$(( ${LANG_BYTES[$lang]:-0} + bytes ))
    LANG_COLORS[$lang]="$(sanitize_color "$color")"
  done <<< "$LANG_ROWS"

  PAGE_REPOS=$(printf '%s' "$REPOS_JSON" | jq -er '.data.user.repositories.nodes | length')
  PAGE_TOTAL_REPOS=$(printf '%s' "$REPOS_JSON" | jq -er '
    .data.user.repositories.totalCount
    | if (type == "number") and (. >= 0) and (. == floor)
      then . else error("invalid totalCount") end
  ')
  if [ -z "$EXPECTED_LANG_REPOS" ]; then
    EXPECTED_LANG_REPOS="$PAGE_TOTAL_REPOS"
  elif (( 10#$PAGE_TOTAL_REPOS != 10#$EXPECTED_LANG_REPOS )); then
    echo "GitHub repository count changed during language pagination" >&2
    exit 1
  fi
  LANG_REPO_COUNT=$((LANG_REPO_COUNT + PAGE_REPOS))
  PAGE_LANG_REPOS=$(printf '%s' "$REPOS_JSON" | jq -er '[.data.user.repositories.nodes[] | select((.languages.edges | length) > 0)] | length')
  TOTAL_LANG_REPOS=$((TOTAL_LANG_REPOS + PAGE_LANG_REPOS))

  HAS_NEXT=$(echo "$REPOS_JSON" | jq -r '.data.user.repositories.pageInfo.hasNextPage | if type == "boolean" then tostring else error("invalid hasNextPage") end')
  echo "  Language page $PAGE done"
  [ "$HAS_NEXT" != "true" ] && break
  NEXT_CURSOR=$(echo "$REPOS_JSON" | jq -r '.data.user.repositories.pageInfo.endCursor | if type == "string" then . else error("invalid endCursor") end')
  if [ -z "$NEXT_CURSOR" ] || [ "$NEXT_CURSOR" = "$CURSOR" ]; then
    echo "GitHub returned an invalid language pagination cursor" >&2
    exit 1
  fi
  CURSOR="$NEXT_CURSOR"
  PAGE=$((PAGE + 1))
done
if (( 10#$EXPECTED_LANG_REPOS != 10#$OPEN_SOURCE_PROJECTS || LANG_REPO_COUNT != 10#$EXPECTED_LANG_REPOS )); then
  echo "GitHub returned incomplete language repository metadata: expected ${OPEN_SOURCE_PROJECTS}, received ${LANG_REPO_COUNT}" >&2
  exit 1
fi

# Sort languages by bytes descending, take top 10
TOTAL_BYTES=0
for lang in "${!LANG_BYTES[@]}"; do
  TOTAL_BYTES=$((TOTAL_BYTES + LANG_BYTES[$lang]))
done
require_integer_at_least "language byte count" "$TOTAL_BYTES" 1
require_integer_at_least "repositories with language data" "$TOTAL_LANG_REPOS" 1

# Build sorted list
SORTED_LANGS=""
for lang in "${!LANG_BYTES[@]}"; do
  SORTED_LANGS+="${LANG_BYTES[$lang]} ${lang}"$'\n'
done
SORTED_LANGS=$(printf "%s" "$SORTED_LANGS" | sort -rn | head -10)

echo ""
echo "Total bytes: $(fmt $TOTAL_BYTES)"
echo "Top languages:"
echo "$SORTED_LANGS" | while read -r bytes lang; do
  [ -z "$lang" ] && continue
  pct=$(calc_pct "$bytes" "$TOTAL_BYTES")
  echo "  $lang: ${pct}% ($(fmt "$bytes") bytes)"
done

# Calculate bytes in human format
BYTES_HUMAN="$(human_bytes "$TOTAL_BYTES")"

# ── Generate stats SVGs ──────────────────────────────────────────────

echo ""
echo "=== Generating stats-light.svg ==="
write_atomically stats-light.svg << SVGEOF
<svg width="495" height="195" viewBox="0 0 495 195" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect x="0.5" y="0.5" rx="4.5" width="494" height="194" fill="#ffffff" stroke="#d0d7de"/>
  <text x="25" y="35" fill="#24292f" font-family="'Segoe UI', Ubuntu, 'Helvetica Neue', sans-serif" font-weight="600" font-size="18">Jeffrey Emanuel's GitHub Stats</text>

  <!-- Row 1: Stars -->
  <circle cx="33" cy="68" r="5" fill="#d4a72c"/>
  <text x="46" y="72" fill="#24292f" font-family="'Segoe UI', Ubuntu, sans-serif" font-size="14">Total Stars</text>
  <text x="190" y="72" fill="#0969da" font-family="'Segoe UI', Ubuntu, sans-serif" font-weight="700" font-size="14">${STARS_FMT}</text>

  <!-- Row 2: Commits -->
  <circle cx="33" cy="98" r="5" fill="#1a7f37"/>
  <text x="46" y="102" fill="#24292f" font-family="'Segoe UI', Ubuntu, sans-serif" font-size="14">Public Commits</text>
  <text x="190" y="102" fill="#0969da" font-family="'Segoe UI', Ubuntu, sans-serif" font-weight="700" font-size="14">${COMMITS_FMT}</text>

  <!-- Row 3: Public Repos -->
  <circle cx="33" cy="128" r="5" fill="#57606a"/>
  <text x="46" y="132" fill="#24292f" font-family="'Segoe UI', Ubuntu, sans-serif" font-size="14">Public Repos</text>
  <text x="190" y="132" fill="#0969da" font-family="'Segoe UI', Ubuntu, sans-serif" font-weight="700" font-size="14">${REPOS_FMT}</text>

  <!-- Row 1 right: Followers -->
  <circle cx="285" cy="68" r="5" fill="#bf3989"/>
  <text x="298" y="72" fill="#24292f" font-family="'Segoe UI', Ubuntu, sans-serif" font-size="14">Followers</text>
  <text x="420" y="72" fill="#0969da" font-family="'Segoe UI', Ubuntu, sans-serif" font-weight="700" font-size="14">${FOLLOWERS_FMT}</text>

  <!-- Row 2 right: Contributions -->
  <circle cx="285" cy="98" r="5" fill="#cf222e"/>
  <text x="298" y="102" fill="#24292f" font-family="'Segoe UI', Ubuntu, sans-serif" font-size="14">Contributions</text>
  <text x="420" y="102" fill="#0969da" font-family="'Segoe UI', Ubuntu, sans-serif" font-weight="700" font-size="14">${CONTRIBUTIONS_FMT}</text>

  <!-- Row 3 right: Following -->
  <circle cx="285" cy="128" r="5" fill="#57606a"/>
  <text x="298" y="132" fill="#24292f" font-family="'Segoe UI', Ubuntu, sans-serif" font-size="14">Following</text>
  <text x="420" y="132" fill="#0969da" font-family="'Segoe UI', Ubuntu, sans-serif" font-weight="700" font-size="14">${FOLLOWING_FMT}</text>

  <!-- Divider -->
  <line x1="260" y1="55" x2="260" y2="145" stroke="#d0d7de" stroke-width="1"/>

  <!-- Updated date -->
  <text x="25" y="172" fill="#6e7781" font-family="'Segoe UI', Ubuntu, sans-serif" font-size="11">Updated ${MONTH}</text>
</svg>
SVGEOF

echo "=== Generating stats.svg (dark) ==="
write_atomically stats.svg << SVGEOF
<svg width="495" height="195" viewBox="0 0 495 195" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect x="0.5" y="0.5" rx="4.5" width="494" height="194" fill="#0d1117" stroke="#30363d"/>
  <text x="25" y="35" fill="#c9d1d9" font-family="'Segoe UI', Ubuntu, 'Helvetica Neue', sans-serif" font-weight="600" font-size="18">Jeffrey Emanuel's GitHub Stats</text>

  <!-- Row 1: Stars -->
  <circle cx="33" cy="68" r="5" fill="#e3b341"/>
  <text x="46" y="72" fill="#c9d1d9" font-family="'Segoe UI', Ubuntu, sans-serif" font-size="14">Total Stars</text>
  <text x="190" y="72" fill="#58a6ff" font-family="'Segoe UI', Ubuntu, sans-serif" font-weight="700" font-size="14">${STARS_FMT}</text>

  <!-- Row 2: Commits -->
  <circle cx="33" cy="98" r="5" fill="#3fb950"/>
  <text x="46" y="102" fill="#c9d1d9" font-family="'Segoe UI', Ubuntu, sans-serif" font-size="14">Public Commits</text>
  <text x="190" y="102" fill="#58a6ff" font-family="'Segoe UI', Ubuntu, sans-serif" font-weight="700" font-size="14">${COMMITS_FMT}</text>

  <!-- Row 3: Public Repos -->
  <circle cx="33" cy="128" r="5" fill="#8b949e"/>
  <text x="46" y="132" fill="#c9d1d9" font-family="'Segoe UI', Ubuntu, sans-serif" font-size="14">Public Repos</text>
  <text x="190" y="132" fill="#58a6ff" font-family="'Segoe UI', Ubuntu, sans-serif" font-weight="700" font-size="14">${REPOS_FMT}</text>

  <!-- Row 1 right: Followers -->
  <circle cx="285" cy="68" r="5" fill="#db61a2"/>
  <text x="298" y="72" fill="#c9d1d9" font-family="'Segoe UI', Ubuntu, sans-serif" font-size="14">Followers</text>
  <text x="420" y="72" fill="#58a6ff" font-family="'Segoe UI', Ubuntu, sans-serif" font-weight="700" font-size="14">${FOLLOWERS_FMT}</text>

  <!-- Row 2 right: Contributions -->
  <circle cx="285" cy="98" r="5" fill="#f78166"/>
  <text x="298" y="102" fill="#c9d1d9" font-family="'Segoe UI', Ubuntu, sans-serif" font-size="14">Contributions</text>
  <text x="420" y="102" fill="#58a6ff" font-family="'Segoe UI', Ubuntu, sans-serif" font-weight="700" font-size="14">${CONTRIBUTIONS_FMT}</text>

  <!-- Row 3 right: Following -->
  <circle cx="285" cy="128" r="5" fill="#8b949e"/>
  <text x="298" y="132" fill="#c9d1d9" font-family="'Segoe UI', Ubuntu, sans-serif" font-size="14">Following</text>
  <text x="420" y="132" fill="#58a6ff" font-family="'Segoe UI', Ubuntu, sans-serif" font-weight="700" font-size="14">${FOLLOWING_FMT}</text>

  <!-- Divider -->
  <line x1="260" y1="55" x2="260" y2="145" stroke="#21262d" stroke-width="1"/>

  <!-- Updated date -->
  <text x="25" y="172" fill="#484f58" font-family="'Segoe UI', Ubuntu, sans-serif" font-size="11">Updated ${MONTH}</text>
</svg>
SVGEOF

# ── Generate language SVGs ────────────────────────────────────────────

echo "=== Generating language SVGs ==="

# Build arrays of top 10 languages sorted by bytes
declare -a TOP_LANGS TOP_PCTS TOP_COLORS
IDX=0
while read -r bytes lang; do
  [ -z "$lang" ] && continue
  TOP_LANGS[IDX]="$lang"
  pct=$(calc_pct "$bytes" "$TOTAL_BYTES")
  TOP_PCTS[IDX]="$pct"
  TOP_COLORS[IDX]="${LANG_COLORS[$lang]:-#888888}"
  IDX=$((IDX + 1))
done <<< "$SORTED_LANGS"

# Calculate bar widths (total bar = 445px)
BAR_WIDTH=445
declare -a BAR_WIDTHS
for i in "${!TOP_PCTS[@]}"; do
  BAR_WIDTHS[i]=$(bar_width "${TOP_PCTS[$i]}" "$BAR_WIDTH")
done

# Take first 5 for left column, next 5 for right column (matching original layout)
LEFT_COUNT=5
RIGHT_COUNT=$((IDX > 5 ? IDX - 5 : 0))
[ $RIGHT_COUNT -gt 5 ] && RIGHT_COUNT=5

# Build progress bar segments
BAR_SEGMENTS_LIGHT=""
BAR_SEGMENTS_DARK=""
X_POS=25
for i in "${!BAR_WIDTHS[@]}"; do
  RX=""
  [ "$i" -eq 0 ] && RX=' rx="3"'
  [ "$i" -eq $((IDX - 1)) ] && RX=' rx="3"'
  BAR_SEGMENTS_LIGHT+="  <rect x=\"$X_POS\" y=\"50\"${RX} width=\"${BAR_WIDTHS[$i]}\" height=\"10\" fill=\"${TOP_COLORS[$i]}\"/>
"
  BAR_SEGMENTS_DARK+="  <rect x=\"$X_POS\" y=\"50\"${RX} width=\"${BAR_WIDTHS[$i]}\" height=\"10\" fill=\"${TOP_COLORS[$i]}\"/>
"
  X_POS=$((X_POS + BAR_WIDTHS[i]))
done

# Build legend entries with fixed percentage columns so short and long names
# have consistent spacing instead of running into their values.
build_legend() {
  local text_fill="$1" pct_fill="$2"
  local entries=""

  # Left column (first 5)
  for i in $(seq 0 $((LEFT_COUNT - 1))); do
    [ "$i" -ge "$IDX" ] && break
    local y_offset=$((82 + i * 25))
    local name="${TOP_LANGS[$i]}"
    local escaped_name
    escaped_name=$(xml_escape "$name")
    entries+="  <g transform=\"translate(25, $y_offset)\">
    <circle cx=\"6\" cy=\"6\" r=\"6\" fill=\"${TOP_COLORS[$i]}\"/>
    <text x=\"18\" y=\"10\" fill=\"${text_fill}\" font-family=\"'Segoe UI', Ubuntu, sans-serif\" font-size=\"13\">${escaped_name}</text>
    <text x=\"105\" y=\"10\" fill=\"${pct_fill}\" font-family=\"'Segoe UI', Ubuntu, sans-serif\" font-size=\"13\">${TOP_PCTS[$i]}%</text>
  </g>
"
  done

  # Right column (next 5)
  for i in $(seq $LEFT_COUNT $((LEFT_COUNT + RIGHT_COUNT - 1))); do
    [ "$i" -ge "$IDX" ] && break
    local y_offset=$((82 + (i - LEFT_COUNT) * 25))
    local name="${TOP_LANGS[$i]}"
    local escaped_name
    escaped_name=$(xml_escape "$name")
    entries+="  <g transform=\"translate(260, $y_offset)\">
    <circle cx=\"6\" cy=\"6\" r=\"6\" fill=\"${TOP_COLORS[$i]}\"/>
    <text x=\"18\" y=\"10\" fill=\"${text_fill}\" font-family=\"'Segoe UI', Ubuntu, sans-serif\" font-size=\"13\">${escaped_name}</text>
    <text x=\"150\" y=\"10\" fill=\"${pct_fill}\" font-family=\"'Segoe UI', Ubuntu, sans-serif\" font-size=\"13\">${TOP_PCTS[$i]}%</text>
  </g>
"
  done

  echo "$entries"
}

LEGEND_LIGHT=$(build_legend "#24292f" "#57606a")
LEGEND_DARK=$(build_legend "#c9d1d9" "#8b949e")

write_atomically languages-light.svg << SVGEOF
<svg width="495" height="285" viewBox="0 0 495 285" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect x="0.5" y="0.5" rx="4.5" width="494" height="284" fill="#ffffff" stroke="#d0d7de"/>
  <text x="25" y="35" fill="#24292f" font-family="'Segoe UI', Ubuntu, 'Helvetica Neue', sans-serif" font-weight="600" font-size="18">Top Languages (by code volume)</text>
  <!-- Progress bar background -->
  <rect x="25" y="50" rx="3" width="445" height="10" fill="#eaeef2"/>
${BAR_SEGMENTS_LIGHT}${LEGEND_LIGHT}  <!-- Summary -->
  <line x1="25" y1="210" x2="470" y2="210" stroke="#d0d7de" stroke-width="1"/>
  <text x="25" y="235" fill="#57606a" font-family="'Segoe UI', Ubuntu, sans-serif" font-size="12">${BYTES_HUMAN} bytes across ${TOTAL_LANG_REPOS} repositories</text>
  <text x="25" y="255" fill="#6e7781" font-family="'Segoe UI', Ubuntu, sans-serif" font-size="11">Updated ${MONTH} · Measured by total code bytes per language</text>
</svg>
SVGEOF

write_atomically languages.svg << SVGEOF
<svg width="495" height="285" viewBox="0 0 495 285" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect x="0.5" y="0.5" rx="4.5" width="494" height="284" fill="#0d1117" stroke="#30363d"/>
  <text x="25" y="35" fill="#c9d1d9" font-family="'Segoe UI', Ubuntu, 'Helvetica Neue', sans-serif" font-weight="600" font-size="18">Top Languages (by code volume)</text>
  <!-- Progress bar background -->
  <rect x="25" y="50" rx="3" width="445" height="10" fill="#161b22"/>
${BAR_SEGMENTS_DARK}${LEGEND_DARK}  <!-- Summary -->
  <line x1="25" y1="210" x2="470" y2="210" stroke="#21262d" stroke-width="1"/>
  <text x="25" y="235" fill="#8b949e" font-family="'Segoe UI', Ubuntu, sans-serif" font-size="12">${BYTES_HUMAN} bytes across ${TOTAL_LANG_REPOS} repositories</text>
  <text x="25" y="255" fill="#484f58" font-family="'Segoe UI', Ubuntu, sans-serif" font-size="11">Updated ${MONTH} · Measured by total code bytes per language</text>
</svg>
SVGEOF

echo ""
echo "=== Generating star history SVGs ==="
# Self-hosted: api.star-history.com serves a 503 in place of the image whenever
# its own GitHub tokens are rate-limited, and takes no token of ours, so there
# is no fixing it from this side. We build the same chart from GitHub's
# `starred_at` timestamps instead. Failure here must not sink the whole run —
# the previous chart stays committed and the other stats still refresh.
STAR_HISTORY_UPDATED=true
if ! python3 scripts/star_history.py; then
  STAR_HISTORY_UPDATED=false
  echo "WARNING: star history generation failed; keeping the existing chart" >&2
fi

echo ""
echo "=== Updating README.md ==="
python3 scripts/update_readme.py

echo ""
if $STAR_HISTORY_UPDATED; then
  echo "=== Done! README.md and all 6 SVGs refreshed. ==="
else
  echo "=== Done! README.md and 4 SVGs refreshed; existing star-history charts preserved. ==="
fi
