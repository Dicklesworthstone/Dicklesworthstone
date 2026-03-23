#!/usr/bin/env bash
set -euo pipefail

# update-stats.sh — Fetches live GitHub stats and regenerates all 4 SVG files.
# Used by the daily GitHub Actions workflow and can be run manually.
# Requires: gh CLI authenticated, jq

USERNAME="Dicklesworthstone"
MONTH=$(date +"%b %Y")

fmt() { printf "%'d" "$1"; }

echo "=== Fetching user profile ==="
PROFILE=$(gh api "users/${USERNAME}")
FOLLOWERS=$(echo "$PROFILE" | jq -r '.followers')
FOLLOWING=$(echo "$PROFILE" | jq -r '.following')
PUBLIC_REPOS=$(echo "$PROFILE" | jq -r '.public_repos')

echo "=== Fetching total stars (paginated) ==="
TOTAL_STARS=0
CURSOR=""
PAGE=1
STARS_QUERY='query($login: String!, $after: String) {
  user(login: $login) {
    repositories(first: 100, after: $after, ownerAffiliations: OWNER) {
      nodes { stargazerCount }
      pageInfo { endCursor hasNextPage }
    }
  }
}'
while true; do
  if [ -z "$CURSOR" ]; then
    RESULT=$(gh api graphql -f query="$STARS_QUERY" -f login="$USERNAME")
  else
    RESULT=$(gh api graphql -f query="$STARS_QUERY" -f login="$USERNAME" -f after="$CURSOR")
  fi
  PAGE_STARS=$(echo "$RESULT" | jq '[.data.user.repositories.nodes[].stargazerCount] | add // 0')
  TOTAL_STARS=$((TOTAL_STARS + PAGE_STARS))
  echo "  Page $PAGE: +$PAGE_STARS stars (total: $TOTAL_STARS)"
  HAS_NEXT=$(echo "$RESULT" | jq -r '.data.user.repositories.pageInfo.hasNextPage')
  [ "$HAS_NEXT" != "true" ] && break
  CURSOR=$(echo "$RESULT" | jq -r '.data.user.repositories.pageInfo.endCursor')
  PAGE=$((PAGE + 1))
done

echo "=== Fetching contributions ==="
CONTRIB=$(gh api graphql -f query='query($login: String!) { user(login: $login) { contributionsCollection { contributionCalendar { totalContributions } } } }' -f login="$USERNAME")
CONTRIBUTIONS=$(echo "$CONTRIB" | jq -r '.data.user.contributionsCollection.contributionCalendar.totalContributions')

echo "=== Fetching total commits ==="
TOTAL_COMMITS=$(gh api "search/commits?q=author:${USERNAME}&per_page=1" | jq -r '.total_count')

echo ""
echo "Stars:         $(fmt $TOTAL_STARS)"
echo "Commits:       $(fmt $TOTAL_COMMITS)"
echo "Public Repos:  $(fmt $PUBLIC_REPOS)"
echo "Followers:     $(fmt $FOLLOWERS)"
echo "Contributions: $(fmt $CONTRIBUTIONS)"
echo "Following:     $(fmt $FOLLOWING)"

STARS_FMT=$(fmt $TOTAL_STARS)
COMMITS_FMT=$(fmt $TOTAL_COMMITS)
REPOS_FMT=$(fmt $PUBLIC_REPOS)
FOLLOWERS_FMT=$(fmt $FOLLOWERS)
CONTRIBUTIONS_FMT=$(fmt $CONTRIBUTIONS)
FOLLOWING_FMT=$(fmt $FOLLOWING)

# ── Fetch language stats ──────────────────────────────────────────────
echo ""
echo "=== Fetching language stats (this takes a moment) ==="

declare -A LANG_BYTES
declare -A LANG_COLORS
CURSOR=""
PAGE=1
LANG_QUERY='query($login: String!, $after: String) {
  user(login: $login) {
    repositories(first: 100, after: $after, ownerAffiliations: OWNER, isFork: false) {
      nodes {
        languages(first: 20, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
      pageInfo { endCursor hasNextPage }
    }
  }
}'
while true; do
  if [ -z "$CURSOR" ]; then
    REPOS_JSON=$(gh api graphql -f query="$LANG_QUERY" -f login="$USERNAME")
  else
    REPOS_JSON=$(gh api graphql -f query="$LANG_QUERY" -f login="$USERNAME" -f after="$CURSOR")
  fi

  # Aggregate language bytes and colors
  while IFS=$'\t' read -r lang bytes color; do
    [ -z "$lang" ] && continue
    LANG_BYTES[$lang]=$(( ${LANG_BYTES[$lang]:-0} + bytes ))
    LANG_COLORS[$lang]="${color}"
  done < <(echo "$REPOS_JSON" | jq -r '.data.user.repositories.nodes[].languages.edges[] | [.node.name, .size, (.node.color // "#888888")] | @tsv')

  HAS_NEXT=$(echo "$REPOS_JSON" | jq -r '.data.user.repositories.pageInfo.hasNextPage')
  echo "  Language page $PAGE done"
  [ "$HAS_NEXT" != "true" ] && break
  CURSOR=$(echo "$REPOS_JSON" | jq -r '.data.user.repositories.pageInfo.endCursor')
  PAGE=$((PAGE + 1))
done

# Sort languages by bytes descending, take top 10
TOTAL_BYTES=0
for lang in "${!LANG_BYTES[@]}"; do
  TOTAL_BYTES=$((TOTAL_BYTES + LANG_BYTES[$lang]))
done

# Build sorted list
SORTED_LANGS=""
for lang in "${!LANG_BYTES[@]}"; do
  SORTED_LANGS+="${LANG_BYTES[$lang]} ${lang}\n"
done
SORTED_LANGS=$(echo -e "$SORTED_LANGS" | sort -rn | head -10)

echo ""
echo "Total bytes: $(fmt $TOTAL_BYTES)"
echo "Top languages:"
echo "$SORTED_LANGS" | while read -r bytes lang; do
  pct=$(echo "scale=1; $bytes * 100 / $TOTAL_BYTES" | bc)
  echo "  $lang: ${pct}% ($(fmt $bytes) bytes)"
done

# Count total repos with language data
TOTAL_LANG_REPOS=$(gh api graphql -f query='query($login: String!) { user(login: $login) { repositories(ownerAffiliations: OWNER, isFork: false) { totalCount } } }' -f login="$USERNAME" | jq -r '.data.user.repositories.totalCount')

# Calculate bytes in human format
if [ "$TOTAL_BYTES" -ge 1000000000 ]; then
  BYTES_HUMAN="$(echo "scale=0; $TOTAL_BYTES / 1000000000" | bc)G"
elif [ "$TOTAL_BYTES" -ge 1000000 ]; then
  BYTES_HUMAN="$(echo "scale=0; $TOTAL_BYTES / 1000000" | bc)M"
else
  BYTES_HUMAN="$(echo "scale=0; $TOTAL_BYTES / 1000" | bc)K"
fi

# ── Generate stats SVGs ──────────────────────────────────────────────

echo ""
echo "=== Generating stats-light.svg ==="
cat > stats-light.svg << SVGEOF
<svg width="495" height="195" viewBox="0 0 495 195" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect x="0.5" y="0.5" rx="4.5" width="494" height="194" fill="#ffffff" stroke="#d0d7de"/>
  <text x="25" y="35" fill="#24292f" font-family="'Segoe UI', Ubuntu, 'Helvetica Neue', sans-serif" font-weight="600" font-size="18">Jeffrey Emanuel's GitHub Stats</text>

  <!-- Row 1: Stars -->
  <circle cx="33" cy="68" r="5" fill="#d4a72c"/>
  <text x="46" y="72" fill="#24292f" font-family="'Segoe UI', Ubuntu, sans-serif" font-size="14">Total Stars</text>
  <text x="190" y="72" fill="#0969da" font-family="'Segoe UI', Ubuntu, sans-serif" font-weight="700" font-size="14">${STARS_FMT}</text>

  <!-- Row 2: Commits -->
  <circle cx="33" cy="98" r="5" fill="#1a7f37"/>
  <text x="46" y="102" fill="#24292f" font-family="'Segoe UI', Ubuntu, sans-serif" font-size="14">Total Commits</text>
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
cat > stats.svg << SVGEOF
<svg width="495" height="195" viewBox="0 0 495 195" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect x="0.5" y="0.5" rx="4.5" width="494" height="194" fill="#0d1117" stroke="#30363d"/>
  <text x="25" y="35" fill="#c9d1d9" font-family="'Segoe UI', Ubuntu, 'Helvetica Neue', sans-serif" font-weight="600" font-size="18">Jeffrey Emanuel's GitHub Stats</text>

  <!-- Row 1: Stars -->
  <circle cx="33" cy="68" r="5" fill="#e3b341"/>
  <text x="46" y="72" fill="#c9d1d9" font-family="'Segoe UI', Ubuntu, sans-serif" font-size="14">Total Stars</text>
  <text x="190" y="72" fill="#58a6ff" font-family="'Segoe UI', Ubuntu, sans-serif" font-weight="700" font-size="14">${STARS_FMT}</text>

  <!-- Row 2: Commits -->
  <circle cx="33" cy="98" r="5" fill="#3fb950"/>
  <text x="46" y="102" fill="#c9d1d9" font-family="'Segoe UI', Ubuntu, sans-serif" font-size="14">Total Commits</text>
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
declare -a TOP_LANGS TOP_BYTES TOP_PCTS TOP_COLORS
IDX=0
while read -r bytes lang; do
  [ -z "$lang" ] && continue
  TOP_LANGS[$IDX]="$lang"
  TOP_BYTES[$IDX]="$bytes"
  pct=$(echo "scale=1; $bytes * 100 / $TOTAL_BYTES" | bc)
  TOP_PCTS[$IDX]="$pct"
  TOP_COLORS[$IDX]="${LANG_COLORS[$lang]:-#888888}"
  IDX=$((IDX + 1))
done <<< "$SORTED_LANGS"

# Calculate bar widths (total bar = 445px)
BAR_WIDTH=445
declare -a BAR_WIDTHS
for i in "${!TOP_PCTS[@]}"; do
  w=$(echo "scale=0; ${TOP_PCTS[$i]} * $BAR_WIDTH / 100" | bc)
  [ "$w" -lt 2 ] && w=2
  BAR_WIDTHS[$i]=$w
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
  X_POS=$((X_POS + BAR_WIDTHS[$i]))
done

# Build legend entries — calculate text x offset based on lang name length
build_legend() {
  local text_fill="$1" pct_fill="$2"
  local entries=""

  # Left column (first 5)
  for i in $(seq 0 $((LEFT_COUNT - 1))); do
    [ $i -ge $IDX ] && break
    local y_offset=$((82 + i * 25))
    local name="${TOP_LANGS[$i]}"
    # Approximate text width: ~8px per char
    local text_x=$((18 + ${#name} * 8 + 4))
    entries+="  <g transform=\"translate(25, $y_offset)\">
    <circle cx=\"6\" cy=\"6\" r=\"6\" fill=\"${TOP_COLORS[$i]}\"/>
    <text x=\"18\" y=\"10\" fill=\"${text_fill}\" font-family=\"'Segoe UI', Ubuntu, sans-serif\" font-size=\"13\">${name}</text>
    <text x=\"${text_x}\" y=\"10\" fill=\"${pct_fill}\" font-family=\"'Segoe UI', Ubuntu, sans-serif\" font-size=\"13\">${TOP_PCTS[$i]}%</text>
  </g>
"
  done

  # Right column (next 5)
  for i in $(seq $LEFT_COUNT $((LEFT_COUNT + RIGHT_COUNT - 1))); do
    [ $i -ge $IDX ] && break
    local y_offset=$((82 + (i - LEFT_COUNT) * 25))
    local name="${TOP_LANGS[$i]}"
    local text_x=$((18 + ${#name} * 8 + 4))
    entries+="  <g transform=\"translate(260, $y_offset)\">
    <circle cx=\"6\" cy=\"6\" r=\"6\" fill=\"${TOP_COLORS[$i]}\"/>
    <text x=\"18\" y=\"10\" fill=\"${text_fill}\" font-family=\"'Segoe UI', Ubuntu, sans-serif\" font-size=\"13\">${name}</text>
    <text x=\"${text_x}\" y=\"10\" fill=\"${pct_fill}\" font-family=\"'Segoe UI', Ubuntu, sans-serif\" font-size=\"13\">${TOP_PCTS[$i]}%</text>
  </g>
"
  done

  echo "$entries"
}

LEGEND_LIGHT=$(build_legend "#24292f" "#57606a")
LEGEND_DARK=$(build_legend "#c9d1d9" "#8b949e")

cat > languages-light.svg << SVGEOF
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

cat > languages.svg << SVGEOF
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
echo "=== Done! All 4 SVGs updated. ==="
