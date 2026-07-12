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
Ten lines is roughly the limit of what a reader can actually follow.
"""

from __future__ import annotations

import bisect
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
USERNAME = "Dicklesworthstone"

MAX_SERIES = 10
CANDIDATES = 20  # top-by-stars pool we pull timelines for
GROWTH_WINDOW_DAYS = 90
SAMPLES = 140  # points per line; keeps the SVG small and the curve smooth

WIDTH, HEIGHT = 900, 420
PAD_L, PAD_R, PAD_T, PAD_B = 58, 240, 44, 46  # PAD_R leaves room for the legend

# Repo names are what the chart is *about*, but several are too long for the
# legend and get truncated into mush ("agentic_coding_flywhe…"). These are the
# names the README already uses for the same projects.
DISPLAY_NAMES = {
    "destructive_command_guard": "DCG",
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

DARK = {
    "bg": "#0d1117",
    "border": "#30363d",
    "grid": "#21262d",
    "text": "#c9d1d9",
    "muted": "#8b949e",
    "faint": "#484f58",
    # Ten lines need ten hues a reader can actually tell apart. The obvious
    # GitHub palette collapses at that size — it yields two greens and two
    # purples that are indistinguishable at a 2px stroke — so these are spread
    # around the wheel instead, in the same order for both themes so a repo
    # keeps its colour whichever one you are looking at.
    "series": [
        "#6cb6ff", "#f0883e", "#ff7b72", "#5ed4c8", "#5bc46b",
        "#e3b341", "#c297d8", "#ff9db8", "#c49a7a", "#9aa4b0",
    ],
}
LIGHT = {
    "bg": "#ffffff",
    "border": "#d0d7de",
    "grid": "#eaeef2",
    "text": "#24292f",
    "muted": "#57606a",
    "faint": "#6e7781",
    "series": [
        "#0969da", "#bc4c00", "#cf222e", "#1b7c83", "#1a7f37",
        "#9a6700", "#8250df", "#bf3989", "#8d5f3d", "#57606a",
    ],
}


def gh(args: list[str]) -> str:
    result = subprocess.run(
        ["gh", *args], capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def candidate_repos() -> list[tuple[str, int]]:
    """Public, non-fork repos ordered by stars — one request."""
    query = """
    query($login: String!) {
      user(login: $login) {
        repositories(privacy: PUBLIC, isFork: false, first: %d,
                     orderBy: {field: STARGAZERS, direction: DESC}) {
          nodes { name stargazerCount }
        }
      }
    }
    """ % CANDIDATES
    payload = json.loads(gh(["api", "graphql", "-f", f"query={query}", "-f", f"login={USERNAME}"]))
    nodes = payload["data"]["user"]["repositories"]["nodes"]
    return [(n["name"], n["stargazerCount"]) for n in nodes]


def starred_at(repo: str) -> list[datetime]:
    """Every star's timestamp, oldest first."""
    raw = gh([
        "api", f"repos/{USERNAME}/{repo}/stargazers",
        "-H", "Accept: application/vnd.github.star+json",
        "--paginate", "--jq", ".[].starred_at",
    ])
    stamps = [
        datetime.fromisoformat(line.replace("Z", "+00:00"))
        for line in raw.splitlines()
        if line.strip()
    ]
    stamps.sort()
    return stamps


def select(series: dict[str, list[datetime]], totals: dict[str, int]) -> list[str]:
    """Pick the repos worth charting: biggest, and fastest-growing.

    Ranking on stars alone charts dead weight — several of the top-ten-by-stars
    repos gained single-digit stars in the last quarter, so they contribute a
    flat line and nothing else. Ranking on growth alone charts noise, because a
    200-star repo doubling is invisible next to a 3,000-star one.

    So each repo is scored on both axes, normalized against the leader of each,
    and the top MAX_SERIES by the sum are charted. A repo earns its line by
    being large, by being on a tear, or by being a bit of both.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=GROWTH_WINDOW_DAYS)
    growth = {
        repo: sum(1 for stamp in stamps if stamp >= cutoff)
        for repo, stamps in series.items()
    }

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


def render(theme: dict, series: dict[str, list[datetime]], order: list[str],
           totals: dict[str, int]) -> str:
    t_min = min(stamps[0] for stamps in series.values())
    t_max = datetime.now(timezone.utc)
    span = (t_max - t_min).total_seconds()

    ticks = [t_min + timedelta(seconds=span * i / (SAMPLES - 1)) for i in range(SAMPLES)]
    curves = {repo: cumulative(series[repo], ticks) for repo in order}

    step = axis_step(max(max(curve) for curve in curves.values()))
    y_max = step * Y_DIVISIONS
    plot_w = WIDTH - PAD_L - PAD_R
    plot_h = HEIGHT - PAD_T - PAD_B

    def x_of(i: int) -> float:
        return PAD_L + plot_w * i / (SAMPLES - 1)

    def y_of(v: int) -> float:
        return PAD_T + plot_h * (1 - v / y_max)

    out: list[str] = [
        f'<svg width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" '
        f'fill="none" xmlns="http://www.w3.org/2000/svg">',
        f'  <rect x="0.5" y="0.5" rx="4.5" width="{WIDTH - 1}" height="{HEIGHT - 1}" '
        f'fill="{theme["bg"]}" stroke="{theme["border"]}"/>',
        f'  <text x="{PAD_L}" y="26" fill="{theme["text"]}" font-family="\'Segoe UI\', Ubuntu, '
        f'sans-serif" font-weight="600" font-size="15">Star History</text>',
    ]

    # Horizontal gridlines + y labels.
    for i in range(Y_DIVISIONS + 1):
        value = step * i
        y = y_of(value)
        out.append(
            f'  <line x1="{PAD_L}" y1="{y:.1f}" x2="{PAD_L + plot_w}" y2="{y:.1f}" '
            f'stroke="{theme["grid"]}" stroke-width="1"/>'
        )
        out.append(
            f'  <text x="{PAD_L - 9}" y="{y + 4:.1f}" fill="{theme["muted"]}" '
            f'font-family="\'Segoe UI\', Ubuntu, sans-serif" font-size="11" '
            f'text-anchor="end">{axis_label(value)}</text>'
        )

    # X labels: first, middle, last.
    for i in (0, (SAMPLES - 1) // 2, SAMPLES - 1):
        out.append(
            f'  <text x="{x_of(i):.1f}" y="{PAD_T + plot_h + 20}" fill="{theme["muted"]}" '
            f'font-family="\'Segoe UI\', Ubuntu, sans-serif" font-size="11" '
            f'text-anchor="middle">{ticks[i].strftime("%b %Y")}</text>'
        )

    # Colour is keyed to star rank, not draw order: the biggest repo should get
    # the boldest hue, not whichever one happens to fall last in the list.
    ranked = sorted(order, key=lambda r: totals[r], reverse=True)
    colour_of = {
        repo: theme["series"][i % len(theme["series"])]
        for i, repo in enumerate(ranked)
    }

    # Curves, smallest first, so the biggest lands on top of the pile.
    for repo in order:
        points = " ".join(
            f"{x_of(i):.1f},{y_of(v):.1f}" for i, v in enumerate(curves[repo])
        )
        out.append(
            f'  <polyline points="{points}" fill="none" stroke="{colour_of[repo]}" '
            f'stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>'
        )

    # Legend, biggest first so it reads top-down.
    legend_x = PAD_L + plot_w + 22
    for row, repo in enumerate(ranked):
        y = PAD_T + 6 + row * 22
        out.append(
            f'  <line x1="{legend_x}" y1="{y}" x2="{legend_x + 16}" y2="{y}" '
            f'stroke="{colour_of[repo]}" stroke-width="2.5" stroke-linecap="round"/>'
        )
        name = DISPLAY_NAMES.get(repo, repo)
        if len(name) > 24:
            name = name[:23] + "…"
        out.append(
            f'  <text x="{legend_x + 24}" y="{y + 4}" fill="{theme["text"]}" '
            f'font-family="\'Segoe UI\', Ubuntu, sans-serif" font-size="11">{name}</text>'
        )

    out.append(
        f'  <text x="{PAD_L}" y="{HEIGHT - 12}" fill="{theme["faint"]}" '
        f'font-family="\'Segoe UI\', Ubuntu, sans-serif" font-size="11">'
        f'Updated {t_max.strftime("%b %Y")}</text>'
    )
    out.append("</svg>")
    return "\n".join(out) + "\n"


def main() -> int:
    candidates = candidate_repos()
    totals = dict(candidates)

    series: dict[str, list[datetime]] = {}
    for repo, stars in candidates:
        print(f"  fetching {repo} ({stars} stars)...", file=sys.stderr)
        stamps = starred_at(repo)
        if stamps:
            series[repo] = stamps

    if not series:
        print("no stargazer data; leaving the chart untouched", file=sys.stderr)
        return 1

    order = select(series, totals)
    print(
        "  charting: " + ", ".join(f"{r} ({totals[r]})" for r in reversed(order)),
        file=sys.stderr,
    )

    (REPO_ROOT / "star_history.svg").write_text(render(DARK, series, order, totals))
    (REPO_ROOT / "star_history-light.svg").write_text(render(LIGHT, series, order, totals))
    return 0


if __name__ == "__main__":
    sys.exit(main())
