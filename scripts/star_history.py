#!/usr/bin/env python3
"""Render a self-hosted star-history chart.

The README used to embed api.star-history.com. That service fetches stargazer
timelines with its own GitHub tokens, and when they are exhausted it serves a
503 ("All GitHub API tokens are rate-limited") in place of the image — so the
chart on the profile silently turns into a broken image with no warning and no
way for us to fix it. Its SVG endpoint accepts no caller-supplied token, so
there is nothing to configure our way out of.

GitHub will hand us the same data directly: the stargazers endpoint returns a
`starred_at` timestamp per star when asked for the star media type. So we build
the series ourselves, on the same schedule as the other SVGs, and commit the
result. No third party, nothing to rate-limit, no expiry.

Selection: the main panel charts MAX_SERIES repos, chosen for total stars *and*
90-day growth. Fourteen lines still fit the dedicated legend without crowding
the plot. A second "Rising fast" panel adds up to MAX_RISING smaller repos with
the sharpest relative growth over the last RISING_WINDOW_DAYS: on the main
panel's multi-year, multi-thousand-star axes those would be invisible.
"""

from __future__ import annotations

import bisect
import functools
import html
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, TypedDict

REPO_ROOT = Path(__file__).resolve().parent.parent
USERNAME = "Dicklesworthstone"

MAX_SERIES = 14
INITIAL_CANDIDATES = 20
GROWTH_WINDOW_DAYS = 90
SAMPLES = 260  # points per line — dense enough that the curves read as curves

# "Rising fast" picks, chosen from repos outside the main MAX_SERIES. The
# thresholds come from the October 2026 distribution of 28-day gains across the
# 112 public repos with at least 20 stars:
# - RISING_MIN_GAIN: gains of 20+ were all genuine surges (new launches at
#   22-132 stars, a 42 -> 77 jump). Below 20 the field was 200-450-star repos
#   creeping up by 3-6% and tiny repos going 0 -> 8 or 1 -> 8, i.e. the
#   "2 -> 6" noise this panel must not chart.
# - RISING_MIN_RELATIVE: the fastest main-panel repo grew 9% in those 28 days
#   and the steady mid-size repos 14-17%; 25% (a quarter in four weeks) sits
#   well above both and below every real surge (83% and up).
# Relative growth is gain / max(stars at window start, RISING_MIN_GAIN), so a
# brand-new repo compares against a floor of 20 instead of dividing by zero,
# and a 3 -> 25 jump cannot outrank a 40 -> 100 one purely by its tiny base.
RISING_WINDOW_DAYS = 28
RISING_MIN_GAIN = 20
RISING_MIN_RELATIVE = 0.25
MAX_RISING = 6
RISING_SAMPLES = 169  # one point every four hours across the 28-day window

# Drawn large and scaled down by the browser, so the strokes and type stay crisp
# on a retina display instead of going soft the way a 900px canvas does.
# HEIGHT is the main panel; the rising panel adds RISING_HEIGHT below it.
WIDTH, HEIGHT = 1440, 660
RISING_HEIGHT = 350
PAD_L, PAD_R, PAD_T, PAD_B = 78, 366, 92, 62  # PAD_R leaves room for the legend
RISING_PAD_T, RISING_PLOT_H = 96, 190  # offsets within the rising panel
FONT = (
    "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', "
    "Helvetica, Arial, sans-serif"
)
# Generous per-character width of the 12px axis labels, used to keep the
# year labels from printing over the dated labels at either end of the axis.
AXIS_CHAR_WIDTH = 7.5
AXIS_LABEL_GAP = 12


class Theme(TypedDict):
    bg: str
    card_top: str
    border: str
    grid: str
    axis: str
    text: str
    muted: str
    faint: str
    accent: str
    series: list[str]


# Repo names are what the chart is *about*, but several are too long for the
# legend and get truncated into mush ("agentic_coding_flywhe…"). These are the
# names the README already uses for the same projects.
DISPLAY_NAMES = {
    "asupersync": "Asupersync",
    "destructive_command_guard": "DCG",
    "llm_aided_ocr": "LLM Aided OCR",
    "pi_agent_rust": "Pi Agent Rust",
    "beads_viewer": "Beads Viewer",
    "beads_rust": "Beads Rust",
    "swiss_army_llama": "Swiss Army Llama",
    "ntm": "NTM",
    "franken_ocr": "FrankenOCR",
    "coding_agent_session_search": "CASS",
    "cass_memory_system": "CASS Memory",
    "agentic_coding_flywheel_setup": "Flywheel Setup",
    "claude_code_agent_farm": "Claude Code Agent Farm",
    "bulk_transcribe_youtube_videos_from_playlist": "Bulk YouTube Transcriber",
    "your-source-to-prompt.html": "Your Source to Prompt",
    "ultimate_bug_scanner": "UBS",
    "mcp_agent_mail": "MCP Agent Mail",
    "automatic_log_collector_and_analyzer": "Automatic Log Collector",
    "sqlalchemy_data_model_visualizer": "SQLAlchemy Visualizer",
}


@functools.cache
def profile_namer() -> Callable[[str], str | None]:
    """The README's own names for repos the chart map above does not cover.

    Rising-fast picks are by nature new or newly noticed repos, so they are
    rarely in DISPLAY_NAMES. Reuse the names update_readme.py gives the same
    repos (its explicit map, then the curated README tables) instead of
    printing raw slugs such as "doodlestein_self_releaser" in the legend.
    Loaded by path so this works both as a script and as `scripts.star_history`.
    """
    try:
        spec = importlib.util.spec_from_file_location(
            "_profile_update_readme", Path(__file__).with_name("update_readme.py")
        )
        if spec is None or spec.loader is None:
            raise ImportError("update_readme.py not found")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        explicit: dict[str, str] = dict(module.DISPLAY_NAMES)
        readme = REPO_ROOT / "README.md"
        curated: dict[str, str] = (
            module.curated_display_names(readme.read_text(encoding="utf-8"))
            if readme.exists()
            else {}
        )
    except (ImportError, OSError, AttributeError, SyntaxError):
        return lambda _repo: None
    return lambda repo: explicit.get(repo) or curated.get(repo)


def display_name(repo: str) -> str:
    return DISPLAY_NAMES.get(repo) or profile_namer()(repo) or repo


DARK: Theme = {
    "bg": "#0d1117",
    "card_top": "#161b22",
    "border": "#30363d",
    "grid": "#21262d",
    "axis": "#30363d",
    "text": "#e6edf3",
    "muted": "#8b949e",
    "faint": "#484f58",
    "accent": "#3fb950",
    # Fourteen lines need fourteen hues a reader can actually tell apart. The
    # obvious GitHub palette collapses at that size — it yields nearby greens
    # and purples that are indistinguishable at a 2px stroke — so these are
    # spread around the wheel instead, in the same order for both themes so a
    # repo keeps its colour whichever one you are looking at.
    "series": [
        "#6cb6ff",
        "#f0883e",
        "#ff7b72",
        "#5ed4c8",
        "#5bc46b",
        "#e3b341",
        "#c297d8",
        "#ff9db8",
        "#c49a7a",
        "#9aa4b0",
        "#56d4ff",
        "#d4ef64",
        "#ff6ec7",
        "#8b9cff",
    ],
}
LIGHT: Theme = {
    "bg": "#ffffff",
    "card_top": "#f6f8fa",
    "border": "#d0d7de",
    "grid": "#eaeef2",
    "axis": "#d0d7de",
    "text": "#1f2328",
    "muted": "#59636e",
    "faint": "#818b98",
    "accent": "#1a7f37",
    "series": [
        "#0969da",
        "#bc4c00",
        "#cf222e",
        "#1b7c83",
        "#1a7f37",
        "#9a6700",
        "#8250df",
        "#bf3989",
        "#8d5f3d",
        "#57606a",
        "#007a99",
        "#597a00",
        "#a40e66",
        "#4056b4",
    ],
}


def gh(args: list[str]) -> str:
    last_error = ""
    for attempt in range(1, 4):
        try:
            result = subprocess.run(
                ["gh", *args], capture_output=True, text=True, check=False, timeout=180
            )
        except subprocess.TimeoutExpired:
            last_error = "request timed out"
        except OSError as exc:
            raise RuntimeError(f"could not run gh: {exc}") from exc
        else:
            if result.returncode == 0:
                return result.stdout
            last_error = result.stderr.strip() or f"gh exited {result.returncode}"
        if attempt < 3:
            print(
                f"  GitHub API attempt {attempt} failed; retrying...",
                file=sys.stderr,
            )
            time.sleep(attempt * 2)
    raise RuntimeError(f"GitHub API request failed after 3 attempts: {last_error}")


def candidate_repos() -> list[tuple[str, int]]:
    """All public, non-fork repos ordered by stars."""
    query = """
    query($login: String!, $after: String) {
      user(login: $login) {
        repositories(privacy: PUBLIC, isFork: false, ownerAffiliations: OWNER,
                     first: 100, after: $after,
                     orderBy: {field: STARGAZERS, direction: DESC}) {
          totalCount
          nodes { name stargazerCount }
          pageInfo { endCursor hasNextPage }
        }
      }
    }
    """
    candidates: list[tuple[str, int]] = []
    seen: set[str] = set()
    cursor: str | None = None
    expected_count: int | None = None
    while True:
        args = [
            "api",
            "graphql",
            "-f",
            f"query={query}",
            "-f",
            f"login={USERNAME}",
        ]
        if cursor is not None:
            args.extend(("-f", f"after={cursor}"))
        try:
            payload = json.JSONDecoder().decode(gh(args))
            repositories = payload["data"]["user"]["repositories"]
            nodes = repositories["nodes"]
            total_count = repositories["totalCount"]
            page_info = repositories["pageInfo"]
            has_next = page_info["hasNextPage"]
            next_cursor = page_info["endCursor"]
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise RuntimeError("GitHub returned invalid repository metadata") from exc
        if (
            not isinstance(nodes, list)
            or not isinstance(total_count, int)
            or isinstance(total_count, bool)
            or total_count < 0
            or not isinstance(has_next, bool)
            or (has_next and (not isinstance(next_cursor, str) or not next_cursor))
        ):
            raise TypeError("GitHub returned invalid repository pagination data")
        if expected_count is None:
            expected_count = total_count
        elif total_count != expected_count:
            raise RuntimeError("GitHub repository count changed during pagination")
        for node in nodes:
            if not isinstance(node, dict):
                raise TypeError("GitHub repository metadata node must be an object")
            name = node.get("name")
            stars = node.get("stargazerCount")
            if (
                not isinstance(name, str)
                or not isinstance(stars, int)
                or isinstance(stars, bool)
            ):
                raise TypeError("GitHub returned invalid repository field types")
            folded_name = name.casefold()
            if not name or stars < 0 or folded_name in seen:
                raise ValueError("GitHub returned invalid repository field values")
            seen.add(folded_name)
            candidates.append((name, stars))
        if not has_next:
            break
        if next_cursor == cursor:
            raise RuntimeError("GitHub returned a repeated repository cursor")
        cursor = next_cursor
    if len(candidates) != expected_count:
        raise RuntimeError(
            "GitHub returned incomplete repository metadata: "
            f"expected {expected_count}, received {len(candidates)}"
        )
    return sorted(candidates, key=lambda item: (-item[1], item[0].casefold()))


def starred_at(repo: str) -> list[datetime]:
    """Every star's timestamp, oldest first."""
    raw = gh(
        [
            "api",
            "-X",
            "GET",
            f"repos/{USERNAME}/{repo}/stargazers",
            "-f",
            "per_page=100",
            "-H",
            "Accept: application/vnd.github.star+json",
            "--paginate",
            "--jq",
            ".[] | [.user.login, .starred_at] | @tsv",
        ]
    )
    by_login: dict[str, datetime] = {}
    for line in raw.splitlines():
        fields = line.split("\t", 1)
        if len(fields) != 2 or not fields[0] or not fields[1]:
            raise RuntimeError(f"GitHub returned invalid stargazer data for {repo}")
        try:
            stamp = datetime.fromisoformat(fields[1].replace("Z", "+00:00"))
        except ValueError as exc:
            raise RuntimeError(
                f"GitHub returned invalid stargazer data for {repo}"
            ) from exc
        if stamp.tzinfo is None or stamp.utcoffset() is None:
            raise RuntimeError(f"GitHub returned invalid stargazer data for {repo}")
        login = fields[0].casefold()
        stamp = stamp.astimezone(timezone.utc)
        previous = by_login.get(login)
        if previous is not None and previous != stamp:
            raise RuntimeError(f"GitHub returned conflicting stargazer data for {repo}")
        by_login[login] = stamp
    stamps = list(by_login.values())
    stamps.sort()
    return stamps


def recent_growth(
    series: dict[str, list[datetime]], snapshot_at: datetime
) -> dict[str, int]:
    """Stars gained per repo in the last GROWTH_WINDOW_DAYS."""
    cutoff = snapshot_at - timedelta(days=GROWTH_WINDOW_DAYS)
    return {
        repo: sum(1 for stamp in stamps if stamp >= cutoff)
        for repo, stamps in series.items()
    }


def select(
    series: dict[str, list[datetime]],
    totals: dict[str, int],
    growth: dict[str, int],
) -> list[str]:
    """Pick the repos worth charting: biggest, and fastest-growing.

    Ranking on stars alone charts dead weight — several top-ranked repositories
    gained single-digit stars in the last quarter, so they contribute a
    flat line and nothing else. Ranking on growth alone charts noise, because a
    200-star repo doubling is invisible next to a 3,000-star one.

    So each repo is scored on both axes, normalized against the leader of each,
    and the top MAX_SERIES by the sum are charted. A repo earns its line by
    being large, by being on a tear, or by being a bit of both.
    """
    max_total = max(totals[repo] for repo in series) or 1
    max_growth = max(growth.values()) or 1

    def score(repo: str) -> float:
        return totals[repo] / max_total + growth[repo] / max_growth

    chosen = sorted(series, key=score, reverse=True)[:MAX_SERIES]
    # Draw the biggest last so it lands on top of the pile.
    return sorted(chosen, key=lambda r: totals[r])


def remaining_cannot_qualify(
    remaining: list[tuple[str, int]],
    series: dict[str, list[datetime]],
    totals: dict[str, int],
    growth: dict[str, int],
) -> bool:
    """Prove that fetching the remaining timelines cannot change the selection."""
    if len(series) < MAX_SERIES:
        return False
    remaining_total = max((stars for _repo, stars in remaining), default=0)
    if remaining_total == 0:
        return True

    # A not-yet-fetched repository cannot have gained more stars during the
    # growth window than its total star count. While that bound stays within
    # both current leaders, fetching it cannot move either normalizer, so the
    # fetched scores are final and the best a remaining repository can score
    # is its star total against both. Past that, a new growth leader would
    # rescale every fetched score and could swap the repositories on either
    # side of the cut without being charted itself, so keep fetching.
    max_total = max(totals[repo] for repo in series)
    max_growth = max(growth.values(), default=0)
    if remaining_total > max_total or remaining_total > max_growth:
        return False
    scores = sorted(
        (totals[repo] / max_total + growth[repo] / max_growth for repo in series),
        reverse=True,
    )
    remaining_upper_bound = remaining_total / max_total + remaining_total / max_growth
    return remaining_upper_bound < scores[MAX_SERIES - 1]


@dataclass(frozen=True)
class RisingPick:
    repo: str
    start: int  # stars before the rising window opened
    gain: int  # stars added inside the window
    relative: float  # gain / max(start, RISING_MIN_GAIN)

    @property
    def total(self) -> int:
        return self.start + self.gain


def rising_candidates(
    series: dict[str, list[datetime]],
    exclude: set[str],
    snapshot_at: datetime,
) -> list[RisingPick]:
    """Every repo outside `exclude`, scored on RISING_WINDOW_DAYS momentum.

    Sorted best-first by relative growth, then absolute gain, then name, so
    the order is total and deterministic. Thresholds are applied separately in
    `rising_picks`, which keeps the full ranking printable for audits.
    """
    cutoff = snapshot_at - timedelta(days=RISING_WINDOW_DAYS)
    scored: list[RisingPick] = []
    for repo, stamps in series.items():
        if repo in exclude:
            continue
        total = bisect.bisect_right(stamps, snapshot_at)
        start = bisect.bisect_left(stamps, cutoff)  # starred strictly before
        gain = total - start
        scored.append(
            RisingPick(repo, start, gain, gain / max(start, RISING_MIN_GAIN))
        )
    scored.sort(key=lambda p: (-p.relative, -p.gain, p.repo.casefold(), p.repo))
    return scored


def rising_picks(
    series: dict[str, list[datetime]],
    exclude: set[str],
    snapshot_at: datetime,
) -> list[RisingPick]:
    """Up to MAX_RISING repos that cleared both the absolute and relative bars."""
    return [
        pick
        for pick in rising_candidates(series, exclude, snapshot_at)
        if pick.gain >= RISING_MIN_GAIN and pick.relative >= RISING_MIN_RELATIVE
    ][:MAX_RISING]


def cumulative(stamps: list[datetime], ticks: list[datetime]) -> list[int]:
    return [bisect.bisect_right(stamps, t) for t in ticks]


Y_DIVISIONS = 4


def axis_step(peak: int) -> int:
    """A round gridline interval, so every tick lands on a value worth printing.

    Picking a ceiling first and dividing by four is what produces ticks like
    3,750 — which then get rendered as "3k" and quietly misinform. Choosing the
    *step* first means every label is exact.
    """
    if peak <= 0:
        return 1
    target = peak / Y_DIVISIONS
    magnitude = 10 ** (len(str(int(target))) - 1)
    for multiple in (1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10):
        step = int(magnitude * multiple)
        if step * Y_DIVISIONS >= peak:
            return step
    return int(magnitude * 10)


def axis_label(value: int) -> str:
    if value >= 1000:
        return f"{value / 1000:g}k"
    return str(value)


def legend_name(repo: str) -> str:
    name = display_name(repo)
    if len(name) > 26:
        name = name[:25] + "…"
    return html.escape(name)


def axis_marks_without_collisions(
    marks: list[tuple[float, str]], left_edge: float, right_edge: float
) -> list[tuple[float, str, str]]:
    """Anchor the end labels inward and drop interior labels that would touch them.

    Returns (x, label, text-anchor) triples. Interior labels are centred on
    their x; the first label starts at the left edge and the last ends at the
    right edge, so they never spill outside the plot.
    """

    def span(x: float, label: str, anchor: str) -> tuple[float, float]:
        width = len(label) * AXIS_CHAR_WIDTH
        if anchor == "start":
            return x, x + width
        if anchor == "end":
            return x - width, x
        return x - width / 2, x + width / 2

    placed: list[tuple[float, str, str]] = []
    for index, (x, label) in enumerate(marks):
        if index == 0 and x <= left_edge + 0.5:
            anchor = "start"
        elif index == len(marks) - 1 and x >= right_edge - 0.5:
            anchor = "end"
        else:
            anchor = "middle"
        placed.append((x, label, anchor))
    first = span(*placed[0])
    last = span(*placed[-1])
    kept = [placed[0]]
    for x, label, anchor in placed[1:-1]:
        left, right = span(x, label, anchor)
        if left >= first[1] + AXIS_LABEL_GAP and right <= last[0] - AXIS_LABEL_GAP:
            kept.append((x, label, anchor))
    if len(placed) > 1:
        kept.append(placed[-1])
    return kept


def render_rising(
    theme: Theme,
    series: dict[str, list[datetime]],
    picks: list[RisingPick],
    snapshot_at: datetime,
) -> list[str]:
    """The "Rising fast" panel: the last RISING_WINDOW_DAYS on their own scale.

    These repos have tens or low hundreds of stars, so on the main panel's
    multi-thousand-star axis spanning years they would be flat lines crushed
    into the final pixels. Here both axes fit them: x covers only the window,
    and y is cumulative stars scaled to the largest pick, so a 42 -> 77 jump
    and a 0 -> 132 launch are both legible.
    """
    top = HEIGHT
    plot_t = top + RISING_PAD_T
    plot_b = plot_t + RISING_PLOT_H
    plot_w = WIDTH - PAD_L - PAD_R
    plot_r = PAD_L + plot_w
    window_start = snapshot_at - timedelta(days=RISING_WINDOW_DAYS)
    span_seconds = (snapshot_at - window_start).total_seconds()
    ticks = [
        window_start + timedelta(seconds=span_seconds * i / (RISING_SAMPLES - 1))
        for i in range(RISING_SAMPLES)
    ]

    def x_at(moment: datetime) -> float:
        offset = (moment - window_start).total_seconds() / span_seconds
        return PAD_L + plot_w * offset

    out: list[str] = [
        f'  <line x1="{PAD_L}" y1="{top + 4}" x2="{WIDTH - 30}" y2="{top + 4}" '
        f'stroke="{theme["border"]}" stroke-width="1"/>',
        f'  <text x="{PAD_L}" y="{top + 46}" fill="{theme["text"]}" font-family="{FONT}" '
        f'font-weight="600" font-size="19">Rising fast</text>',
        f'  <text x="{PAD_L}" y="{top + 69}" fill="{theme["muted"]}" font-family="{FONT}" '
        f'font-size="13">Outside the top {MAX_SERIES}: gained {RISING_MIN_GAIN}+ stars '
        f"and grew {RISING_MIN_RELATIVE:.0%}+ in the last {RISING_WINDOW_DAYS} days "
        f"&#183; plotted on their own scale</text>",
    ]

    # Weekly date marks; the collision pass keeps a non-multiple-of-seven
    # window from printing its last weekly label over the end date.
    marks = [
        (x_at(window_start + timedelta(days=day)), window_start + timedelta(days=day))
        for day in range(0, RISING_WINDOW_DAYS + 1, 7)
    ]
    if marks[-1][1] != snapshot_at:
        marks.append((x_at(snapshot_at), snapshot_at))
    labelled = axis_marks_without_collisions(
        [(x, f"{moment:%b} {moment.day}") for x, moment in marks], PAD_L, plot_r
    )

    if not picks:
        out.append(
            f'  <line x1="{PAD_L}" y1="{plot_b}" x2="{plot_r}" y2="{plot_b}" '
            f'stroke="{theme["axis"]}" stroke-width="1"/>'
        )
        out.append(
            f'  <text x="{PAD_L + plot_w / 2:.1f}" y="{plot_t + RISING_PLOT_H / 2:.1f}" '
            f'fill="{theme["muted"]}" font-family="{FONT}" font-size="14" '
            f'text-anchor="middle">No repository outside the top {MAX_SERIES} cleared '
            f"both bars this time.</text>"
        )
    else:
        curves = {pick.repo: cumulative(series[pick.repo], ticks) for pick in picks}
        step = axis_step(max(curve[-1] for curve in curves.values()))
        y_max = step * Y_DIVISIONS

        def y_of(value: int) -> float:
            return plot_t + RISING_PLOT_H * (1 - value / y_max)

        for i in range(Y_DIVISIONS + 1):
            value = step * i
            y = y_of(value)
            dash = "" if i == 0 else ' stroke-dasharray="3 5"'
            colour = theme["axis"] if i == 0 else theme["grid"]
            out.append(
                f'  <line x1="{PAD_L}" y1="{y:.1f}" x2="{plot_r}" y2="{y:.1f}" '
                f'stroke="{colour}" stroke-width="1"{dash}/>'
            )
            out.append(
                f'  <text x="{PAD_L - 12}" y="{y + 4:.1f}" fill="{theme["muted"]}" '
                f'font-family="{FONT}" font-size="12" text-anchor="end">'
                f"{axis_label(value)}</text>"
            )
        for x, _moment in marks[1:-1]:
            out.append(
                f'  <line x1="{x:.1f}" y1="{plot_t}" x2="{x:.1f}" y2="{plot_b}" '
                f'stroke="{theme["grid"]}" stroke-width="1" stroke-dasharray="3 5"/>'
            )

        # Each panel has its own legend beside it, so the palette restarts here:
        # within the panel every line is distinct, which is what a reader
        # matches against. Colour follows rank, best riser first.
        colour_of = {
            pick.repo: theme["series"][i % len(theme["series"])]
            for i, pick in enumerate(picks)
        }

        def x_of(i: int) -> float:
            return PAD_L + plot_w * i / (RISING_SAMPLES - 1)

        # Draw the leader last so it sits on top.
        for pick in reversed(picks):
            curve = curves[pick.repo]
            first = next((i for i, v in enumerate(curve) if v > 0), len(curve) - 1)
            start = max(first - 1, 0)
            pts = " ".join(
                f"{x_of(i):.1f},{y_of(curve[i]):.1f}" for i in range(start, len(curve))
            )
            out.append(
                f'  <polyline points="{pts}" fill="none" stroke="{colour_of[pick.repo]}" '
                f'stroke-width="2.25" stroke-linejoin="round" stroke-linecap="round"/>'
            )
        for pick in reversed(picks):
            out.append(
                f'  <circle cx="{plot_r:.1f}" cy="{y_of(curves[pick.repo][-1]):.1f}" '
                f'r="4.5" fill="{theme["bg"]}" stroke="{colour_of[pick.repo]}" '
                f'stroke-width="2.25"/>'
            )

        legend_x = plot_r + 34
        legend_r = WIDTH - 30
        for row, pick in enumerate(picks):
            y = plot_t + 10 + row * 26
            colour = colour_of[pick.repo]
            out.append(
                f'  <rect x="{legend_x}" y="{y - 5}" width="14" height="4" rx="2" '
                f'fill="{colour}"/>'
            )
            out.append(
                f'  <text x="{legend_x + 24}" y="{y}" fill="{theme["text"]}" '
                f'font-family="{FONT}" font-size="13">{legend_name(pick.repo)}</text>'
            )
            change = (
                "new" if pick.start == 0 else f"+{pick.gain * 100 / pick.start:,.0f}%"
            )
            out.append(
                f'  <text x="{legend_r}" y="{y}" fill="{theme["muted"]}" '
                f'font-family="{FONT}" font-size="12" text-anchor="end">'
                f"{pick.total:,}"
                f'  <tspan fill="{theme["accent"]}">+{pick.gain:,}</tspan>'
                f" ({change})</text>"
            )

    for x, label, anchor in labelled:
        out.append(
            f'  <text x="{x:.1f}" y="{plot_b + 24}" fill="{theme["muted"]}" '
            f'font-family="{FONT}" font-size="12" text-anchor="{anchor}">{label}</text>'
        )
    return out


def render(
    theme: Theme,
    series: dict[str, list[datetime]],
    order: list[str],
    totals: dict[str, int],
    growth: dict[str, int],
    snapshot_at: datetime,
    rising: list[RisingPick] | None = None,
) -> str:
    """Draw the main panel, plus the rising panel below it when `rising` is given.

    An empty `rising` list still draws the panel, with a note that nothing
    qualified, so the README layout and alt text stay true either way.
    """
    height = HEIGHT + (RISING_HEIGHT if rising is not None else 0)
    t_min = min(series[repo][0] for repo in order)
    t_max = snapshot_at
    span = max((t_max - t_min).total_seconds(), 1)

    ticks = [
        t_min + timedelta(seconds=span * i / (SAMPLES - 1)) for i in range(SAMPLES)
    ]
    curves = {repo: cumulative(series[repo], ticks) for repo in order}

    step = axis_step(max(max(curve) for curve in curves.values()))
    y_max = step * Y_DIVISIONS
    plot_w = WIDTH - PAD_L - PAD_R
    plot_h = HEIGHT - PAD_T - PAD_B
    plot_r = PAD_L + plot_w
    plot_b = PAD_T + plot_h

    def x_of(i: int) -> float:
        return PAD_L + plot_w * i / (SAMPLES - 1)

    def y_of(v: int) -> float:
        return PAD_T + plot_h * (1 - v / y_max)

    # Colour is keyed to star rank, not draw order: the biggest repo should get
    # the boldest hue, not whichever one happens to fall last in the list.
    ranked = sorted(order, key=lambda r: totals[r], reverse=True)
    colour_of = {
        repo: theme["series"][i % len(theme["series"])] for i, repo in enumerate(ranked)
    }

    aria = f"Star history for {len(order)} leading repositories"
    if rising is not None:
        aria += (
            f" and {len(rising)} smaller "
            f"{'repository' if len(rising) == 1 else 'repositories'} rising fastest "
            f"over the last {RISING_WINDOW_DAYS} days"
        )
    out: list[str] = [
        (
            f'<svg width="{WIDTH}" height="{height}" viewBox="0 0 {WIDTH} {height}" '
            f'fill="none" xmlns="http://www.w3.org/2000/svg" '
            f'role="img" aria-label="{aria}">'
        ),
        "  <defs>",
    ]

    # No area fills: fourteen of them overlapping turns the lower half of the plot
    # into brown mush. With this many series the lines have to carry it alone.
    out.append(
        f'    <linearGradient id="card" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" stop-color="{theme["card_top"]}"/>'
        f'<stop offset="100%" stop-color="{theme["bg"]}"/>'
        f"</linearGradient>"
    )
    out.append("  </defs>")

    out.append(
        f'  <rect x="0.5" y="0.5" rx="12" width="{WIDTH - 1}" height="{height - 1}" '
        f'fill="url(#card)" stroke="{theme["border"]}"/>'
    )

    # Header.
    out.append(
        f'  <text x="{PAD_L}" y="46" fill="{theme["text"]}" font-family="{FONT}" '
        f'font-weight="600" font-size="21">Star History</text>'
    )
    total_stars = sum(totals[r] for r in order)
    total_growth = sum(growth[r] for r in order)
    out.append(
        f'  <text x="{PAD_L}" y="69" fill="{theme["muted"]}" font-family="{FONT}" '
        f'font-size="13">Top {len(order)} by stars and {GROWTH_WINDOW_DAYS}-day growth'
        f" &#183; {total_stars:,} stars, {total_growth:,} in the last "
        f"{GROWTH_WINDOW_DAYS} days</text>"
    )

    # Gridlines + y labels.
    for i in range(Y_DIVISIONS + 1):
        value = step * i
        y = y_of(value)
        dash = "" if i == 0 else ' stroke-dasharray="3 5"'
        colour = theme["axis"] if i == 0 else theme["grid"]
        out.append(
            f'  <line x1="{PAD_L}" y1="{y:.1f}" x2="{plot_r}" y2="{y:.1f}" '
            f'stroke="{colour}" stroke-width="1"{dash}/>'
        )
        out.append(
            f'  <text x="{PAD_L - 12}" y="{y + 4:.1f}" fill="{theme["muted"]}" '
            f'font-family="{FONT}" font-size="12" text-anchor="end">'
            f"{axis_label(value)}</text>"
        )

    # X labels at the start of each calendar year the chart spans, plus today.
    year_marks: list[tuple[int, str]] = []
    seen_years: set[int] = set()
    for i, tick in enumerate(ticks):
        if tick.year not in seen_years:
            seen_years.add(tick.year)
            year_marks.append((i, tick.strftime("%b %Y") if i == 0 else str(tick.year)))
    final_mark = (SAMPLES - 1, ticks[-1].strftime("%b %Y"))
    if year_marks[-1][0] == final_mark[0]:
        year_marks[-1] = final_mark
    else:
        year_marks.append(final_mark)

    def label_span(i: int, label: str) -> tuple[float, float]:
        width = len(label) * AXIS_CHAR_WIDTH
        x = x_of(i)
        if i == 0:
            return x, x + width
        if i == SAMPLES - 1:
            return x - width, x
        return x - width / 2, x + width / 2

    first_span = label_span(*year_marks[0])
    final_span = label_span(*year_marks[-1])

    for i, label in year_marks:
        x = x_of(i)
        if i not in (0, SAMPLES - 1):
            out.append(
                f'  <line x1="{x:.1f}" y1="{PAD_T}" x2="{x:.1f}" y2="{plot_b}" '
                f'stroke="{theme["grid"]}" stroke-width="1" stroke-dasharray="3 5"/>'
            )
            # From January until about April the new year's label sits on top
            # of the end-of-axis date (and likewise for a chart that starts
            # late in a year), so it keeps its gridline but drops its text.
            left, right = label_span(i, label)
            if (
                left < first_span[1] + AXIS_LABEL_GAP
                or right > final_span[0] - AXIS_LABEL_GAP
            ):
                continue
        anchor = "start" if i == 0 else ("end" if i == SAMPLES - 1 else "middle")
        out.append(
            f'  <text x="{x:.1f}" y="{plot_b + 24}" fill="{theme["muted"]}" '
            f'font-family="{FONT}" font-size="12" text-anchor="{anchor}">{label}</text>'
        )

    # A repo's line starts at its first star, not at the left edge. Drawing from
    # the edge lays a flat zero line across years in which the repo did not
    # exist — DCG is three years of nothing followed by a vertical wall — which
    # is noise pretending to be data.
    def visible(repo: str) -> list[tuple[float, float]]:
        curve = curves[repo]
        first = next((i for i, v in enumerate(curve) if v > 0), len(curve) - 1)
        start = max(first - 1, 0)  # keep one zero point so the line rises off the axis
        return [(x_of(i), y_of(curve[i])) for i in range(start, len(curve))]

    paths = {repo: visible(repo) for repo in order}

    for repo in order:
        pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in paths[repo])
        out.append(
            f'  <polyline points="{pts}" fill="none" stroke="{colour_of[repo]}" '
            f'stroke-width="2.25" stroke-linejoin="round" stroke-linecap="round"/>'
        )

    # A dot at each series\' present-day value, so the eye can land the line in
    # the legend without tracing it back.
    for repo in order:
        x, y = x_of(SAMPLES - 1), y_of(curves[repo][-1])
        out.append(
            f'  <circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="{theme["bg"]}" '
            f'stroke="{colour_of[repo]}" stroke-width="2.25"/>'
        )

    # Legend: name, total, and the quarter\'s gain — the growth column is the
    # whole reason these repositories were chosen, so it belongs on the chart.
    legend_x = plot_r + 34
    legend_r = WIDTH - 30
    for row, repo in enumerate(ranked):
        y = PAD_T + 10 + row * 26
        colour = colour_of[repo]
        out.append(
            f'  <rect x="{legend_x}" y="{y - 5}" width="14" height="4" rx="2" fill="{colour}"/>'
        )
        out.append(
            f'  <text x="{legend_x + 24}" y="{y}" fill="{theme["text"]}" '
            f'font-family="{FONT}" font-size="13">{legend_name(repo)}</text>'
        )
        gain = growth[repo]
        gain_text = f"+{gain:,}" if gain else "\u2014"
        out.append(
            f'  <text x="{legend_r}" y="{y}" fill="{theme["muted"]}" font-family="{FONT}" '
            f'font-size="12" text-anchor="end">{totals[repo]:,}'
            f'  <tspan fill="{theme["accent"]}">{gain_text}</tspan></text>'
        )

    if rising is not None:
        out.extend(render_rising(theme, series, rising, snapshot_at))

    out.append(
        f'  <text x="{PAD_L}" y="{height - 18}" fill="{theme["faint"]}" '
        f'font-family="{FONT}" font-size="11">Generated from GitHub stargazer '
        f"timestamps &#183; updated {t_max.strftime('%d %b %Y')}</text>"
    )
    out.append("</svg>")
    return "\n".join(out) + "\n"


def write_atomically(path: Path, content: str) -> None:
    """Replace an SVG only after its complete new contents are on disk."""
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            os.fchmod(handle.fileno(), 0o644)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def write_svg_pair(artifacts: list[tuple[Path, str]]) -> None:
    """Write a theme pair together, restoring the old pair on any failure."""
    originals = {
        path: path.read_text(encoding="utf-8") if path.exists() else None
        for path, _content in artifacts
    }
    written: list[Path] = []
    try:
        for path, content in artifacts:
            write_atomically(path, content)
            written.append(path)
    except BaseException as exc:
        rollback_failures: list[str] = []
        for path in reversed(written):
            try:
                original = originals[path]
                if original is None:
                    path.unlink(missing_ok=True)
                else:
                    write_atomically(path, original)
            except OSError:
                rollback_failures.append(path.name)
        if rollback_failures:
            names = ", ".join(rollback_failures)
            raise RuntimeError(
                f"could not restore star-history artifact(s): {names}"
            ) from exc
        raise


def main() -> int:
    candidates = candidate_repos()
    totals = dict(candidates)

    series: dict[str, list[datetime]] = {}
    snapshot_at = datetime.now(timezone.utc)
    growth: dict[str, int] = {}
    for index, (repo, stars) in enumerate(candidates):
        print(f"  fetching {repo} ({stars} stars)...", file=sys.stderr)
        stamps = starred_at(repo)
        # Anchor the chart after the response arrives so a star added while a
        # timeline is being fetched cannot be counted in the legend while
        # being clipped from the plotted endpoint.
        snapshot_at = datetime.now(timezone.utc)
        if stars > 0 and not stamps:
            raise RuntimeError(
                f"GitHub returned no stargazer timestamps for {repo} "
                f"despite reporting {stars} stars"
            )
        if stamps:
            series[repo] = stamps
            totals[repo] = len(stamps)
        growth = recent_growth(series, snapshot_at)
        fetched_count = index + 1
        remaining = candidates[fetched_count:]
        # Candidates arrive in descending star order, so once the next one
        # has fewer than RISING_MIN_GAIN stars, none of the rest can gain that
        # many in the rising window either; until then every timeline counts.
        rising_possible = bool(remaining) and remaining[0][1] >= RISING_MIN_GAIN
        if (
            fetched_count >= INITIAL_CANDIDATES
            and not rising_possible
            and remaining_cannot_qualify(remaining, series, totals, growth)
        ):
            print(
                f"  selection proven after {fetched_count} of "
                f"{len(candidates)} repository timelines",
                file=sys.stderr,
            )
            break

    if not series:
        print("no stargazer data; leaving the chart untouched", file=sys.stderr)
        return 1

    order = select(series, totals, growth)
    print(
        "  charting: "
        + ", ".join(f"{r} ({totals[r]}, +{growth[r]})" for r in reversed(order)),
        file=sys.stderr,
    )
    ranked_risers = rising_candidates(series, set(order), snapshot_at)
    rising = rising_picks(series, set(order), snapshot_at)
    print(
        f"  rising candidates ({RISING_WINDOW_DAYS}d gain >= {RISING_MIN_GAIN // 2}): "
        + ", ".join(
            f"{p.repo} ({p.start}->{p.total}, x{p.relative:.2f})"
            for p in ranked_risers
            if p.gain >= RISING_MIN_GAIN // 2
        ),
        file=sys.stderr,
    )
    print(
        "  rising: "
        + (", ".join(f"{p.repo} (+{p.gain})" for p in rising) or "none qualified"),
        file=sys.stderr,
    )

    dark = render(DARK, series, order, totals, growth, snapshot_at, rising)
    light = render(LIGHT, series, order, totals, growth, snapshot_at, rising)
    write_svg_pair(
        [
            (REPO_ROOT / "star_history.svg", dark),
            (REPO_ROOT / "star_history-light.svg", light),
        ]
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
