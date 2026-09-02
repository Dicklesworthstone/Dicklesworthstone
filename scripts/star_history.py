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

Selection: at most MAX_SERIES repos, chosen for total stars *and* recent growth.
Fourteen lines still fit the dedicated legend without crowding the plot.
"""

from __future__ import annotations

import bisect
import html
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TypedDict

REPO_ROOT = Path(__file__).resolve().parent.parent
USERNAME = "Dicklesworthstone"

MAX_SERIES = 14
CANDIDATES = 20  # top-by-stars pool we pull timelines for
GROWTH_WINDOW_DAYS = 90
SAMPLES = 260  # points per line — dense enough that the curves read as curves

# Drawn large and scaled down by the browser, so the strokes and type stay crisp
# on a retina display instead of going soft the way a 900px canvas does.
WIDTH, HEIGHT = 1440, 660
PAD_L, PAD_R, PAD_T, PAD_B = 78, 366, 92, 62  # PAD_R leaves room for the legend
FONT = (
    "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', "
    "Helvetica, Arial, sans-serif"
)


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
    try:
        result = subprocess.run(
            ["gh", *args], capture_output=True, text=True, check=False, timeout=180
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("GitHub API request timed out") from exc
    if result.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def candidate_repos() -> list[tuple[str, int]]:
    """Public, non-fork repos ordered by stars — one request."""
    query = f"""
    query($login: String!) {{
      user(login: $login) {{
        repositories(privacy: PUBLIC, isFork: false, first: {CANDIDATES},
                     orderBy: {{field: STARGAZERS, direction: DESC}}) {{
          nodes {{ name stargazerCount }}
        }}
      }}
    }}
    """
    try:
        payload = json.JSONDecoder().decode(
            gh(
                [
                    "api",
                    "graphql",
                    "-f",
                    f"query={query}",
                    "-f",
                    f"login={USERNAME}",
                ]
            )
        )
        nodes = payload["data"]["user"]["repositories"]["nodes"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise RuntimeError("GitHub returned invalid repository metadata") from exc
    if not isinstance(nodes, list):
        raise TypeError("GitHub repository metadata nodes must be a list")
    candidates = []
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
        if not name or stars < 0:
            raise ValueError("GitHub returned invalid repository field values")
        candidates.append((name, stars))
    return candidates


def starred_at(repo: str) -> list[datetime]:
    """Every star's timestamp, oldest first."""
    raw = gh(
        [
            "api",
            f"repos/{USERNAME}/{repo}/stargazers",
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
        by_login[fields[0]] = stamp.astimezone(timezone.utc)
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


def render(
    theme: Theme,
    series: dict[str, list[datetime]],
    order: list[str],
    totals: dict[str, int],
    growth: dict[str, int],
    snapshot_at: datetime,
) -> str:
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

    out: list[str] = [
        (
            f'<svg width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" '
            f'fill="none" xmlns="http://www.w3.org/2000/svg" '
            f'role="img" aria-label="Star history for {len(order)} leading repositories">'
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
        f'  <rect x="0.5" y="0.5" rx="12" width="{WIDTH - 1}" height="{HEIGHT - 1}" '
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

    for i, label in year_marks:
        x = x_of(i)
        if i not in (0, SAMPLES - 1):
            out.append(
                f'  <line x1="{x:.1f}" y1="{PAD_T}" x2="{x:.1f}" y2="{plot_b}" '
                f'stroke="{theme["grid"]}" stroke-width="1" stroke-dasharray="3 5"/>'
            )
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
        name = DISPLAY_NAMES.get(repo, repo)
        if len(name) > 26:
            name = name[:25] + "\u2026"
        name = html.escape(name)
        out.append(
            f'  <text x="{legend_x + 24}" y="{y}" fill="{theme["text"]}" '
            f'font-family="{FONT}" font-size="13">{name}</text>'
        )
        gain = growth[repo]
        gain_text = f"+{gain:,}" if gain else "\u2014"
        out.append(
            f'  <text x="{legend_r}" y="{y}" fill="{theme["muted"]}" font-family="{FONT}" '
            f'font-size="12" text-anchor="end">{totals[repo]:,}'
            f'  <tspan fill="{theme["accent"]}">{gain_text}</tspan></text>'
        )

    out.append(
        f'  <text x="{PAD_L}" y="{HEIGHT - 18}" fill="{theme["faint"]}" '
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


def main() -> int:
    candidates = candidate_repos()
    totals = dict(candidates)

    series: dict[str, list[datetime]] = {}
    for repo, stars in candidates:
        print(f"  fetching {repo} ({stars} stars)...", file=sys.stderr)
        stamps = starred_at(repo)
        if stars > 0 and not stamps:
            raise RuntimeError(
                f"GitHub returned no stargazer timestamps for {repo} "
                f"despite reporting {stars} stars"
            )
        if stamps:
            series[repo] = stamps
            totals[repo] = len(stamps)

    if not series:
        print("no stargazer data; leaving the chart untouched", file=sys.stderr)
        return 1

    snapshot_at = datetime.now(timezone.utc)
    growth = recent_growth(series, snapshot_at)
    order = select(series, totals, growth)
    print(
        "  charting: "
        + ", ".join(f"{r} ({totals[r]}, +{growth[r]})" for r in reversed(order)),
        file=sys.stderr,
    )

    dark = render(DARK, series, order, totals, growth, snapshot_at)
    light = render(LIGHT, series, order, totals, growth, snapshot_at)
    write_atomically(REPO_ROOT / "star_history.svg", dark)
    write_atomically(REPO_ROOT / "star_history-light.svg", light)
    return 0


if __name__ == "__main__":
    sys.exit(main())
