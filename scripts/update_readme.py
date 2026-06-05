#!/usr/bin/env python3
"""Refresh mechanical README.md sections from live GitHub/site data."""

from __future__ import annotations

import html
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import parse_qsl, quote, urlencode


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
WRITING_URL = os.environ.get("WRITING_URL", "https://www.jeffreyemanuel.com/writing")
SITE_ROOT = "https://www.jeffreyemanuel.com"
JSON_DECODER = json.JSONDecoder()


LANG_LOGOS = {
    "Bash": "gnu-bash",
    "Go": "go",
    "HTML": "html5",
    "JavaScript": "javascript",
    "Python": "python",
    "Rust": "rust",
    "Shell": "gnu-bash",
    "TypeScript": "typescript",
}

LANG_COLORS = {
    "Bash": "4EAA25",
    "Go": "00ADD8",
    "HTML": "E34F26",
    "JavaScript": "F7DF1E",
    "Python": "3776AB",
    "Rust": "000000",
    "Shell": "4EAA25",
    "TypeScript": "3178C6",
}

DISPLAY_NAMES = {
    "asupersync": "ASupersync",
    "coding_agent_session_search": "CASS",
    "eidetic_engine_cli": "Eidetic Engine CLI",
    "franken_engine": "FrankenEngine",
    "franken_networkx": "FrankenNetworkX",
    "franken_node": "FrankenNode",
    "franken_numpy": "FrankenNumPy",
    "franken_whisper": "FrankenWhisper",
    "frankenfs": "FrankenFS",
    "frankenjax": "FrankenJAX",
    "frankenlibc": "FrankenLibC",
    "frankenmermaid": "FrankenMermaid",
    "frankenpandas": "FrankenPandas",
    "frankenredis": "FrankenRedis",
    "frankenscipy": "FrankenSciPy",
    "frankensearch": "FrankenSearch",
    "frankensqlite": "FrankenSQLite",
    "frankenterm": "FrankenTerm",
    "frankentorch": "FrankenTorch",
    "frankentui": "FrankenTUI",
    "mcp_agent_mail": "MCP Agent Mail",
    "mcp_agent_mail_rust": "MCP Agent Mail Rust",
    "ntm": "NTM",
    "pi_agent_rust": "Pi Agent Rust",
    "xf": "XF",
}

RECENT_EXCLUDE = {
    "Dicklesworthstone",
    "homebrew-tap",
    "scoop-bucket",
}


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def replace_line_any(text: str, prefixes: list[str], replacement: str) -> str:
    pattern = re.compile(
        r"^(?:" + "|".join(re.escape(prefix) for prefix in prefixes) + r").*$",
        re.MULTILINE,
    )
    updated, count = pattern.subn(replacement, text, count=1)
    if count != 1:
        raise SystemExit(
            "Could not find README line starting with one of: " + ", ".join(prefixes)
        )
    return updated


def existing_match(text: str, pattern: str, default: str) -> str:
    match = re.search(pattern, text)
    return match.group(1) if match else default


def existing_badge_message(
    text: str, labels: list[str], legacy_pattern: str, default: str
) -> str:
    static_pattern = re.compile(
        r"!\[[^\]]+\]\(https://img\.shields\.io/static/v1\?(?P<query>[^)]*)\)"
    )
    for match in static_pattern.finditer(text):
        params = dict(parse_qsl(match.group("query"), keep_blank_values=True))
        if params.get("label") in labels and params.get("message"):
            return params["message"]
    return existing_match(text, legacy_pattern, default)


def decode_json(text: str) -> object:
    return JSON_DECODER.decode(text)


def repo_metadata_payload() -> str | None:
    content = env("RECENT_REPOS_JSON_CONTENT")
    if content:
        return content

    path = env("RECENT_REPOS_JSON")
    if not path:
        return None
    return Path(path).read_text(encoding="utf-8")


def between_markers(text: str, start: str, end: str, block: str) -> str:
    marker_pattern = re.compile(
        rf"{re.escape(start)}\n.*?\n{re.escape(end)}",
        re.DOTALL,
    )
    replacement = f"{start}\n{block.rstrip()}\n{end}"
    updated, count = marker_pattern.subn(replacement, text, count=1)
    if count != 1:
        raise SystemExit(f"Could not locate complete README marker pair: {start} / {end}")
    return updated


def replace_section_range(
    text: str, start_pattern: str, end_pattern: str, replacement: str
) -> str:
    pattern = re.compile(
        f"(?P<start>{start_pattern}).*?(?P<end>{end_pattern})",
        re.DOTALL,
    )

    def repl(match: re.Match[str]) -> str:
        return f"{match.group('start')}{replacement.rstrip()}\n\n{match.group('end')}"

    updated, count = pattern.subn(repl, text, count=1)
    if count != 1:
        raise SystemExit("Could not locate README section range for replacement")
    return updated


def round_badge_line(
    label: str, value: str, logo: str = "github", alt_label: str | None = None
) -> str:
    query = urlencode(
        {
            "label": label,
            "message": value,
            "color": "2b2b2b",
            "style": "flat-square",
            "logo": logo,
            "logoColor": "white",
        }
    )
    alt = f"{alt_label or label}: {value}"
    return f"![{alt}](https://img.shields.io/static/v1?{query})"


def discord_badge_line(member_count: str) -> str:
    value = quote(f"{member_count}_members", safe=",_")
    return (
        "[![Discord]"
        f"(https://img.shields.io/badge/Flywheel_Hub-{value}-5865F2"
        "?style=flat-square&logo=discord&logoColor=white)]"
        "(https://discord.gg/gnCHsYDR25)"
    )


def lang_badge(language: str | None, color: str | None) -> str:
    name = language or "Code"
    logo = LANG_LOGOS.get(name, "")
    color_value = (color or LANG_COLORS.get(name) or "#2b2b2b").lstrip("#") or "2b2b2b"
    logo_part = f"&logo={quote(logo)}&logoColor=white" if logo else ""
    return (
        f"![{name}](https://img.shields.io/badge/-{quote(name)}-{color_value}"
        f"?style=flat-square{logo_part})"
    )


def static_star_badge(repo_name: str, stars: int, color: str) -> str:
    value = quote(f"{stars:,}", safe=",")
    color_value = quote(color.lstrip("#") or "blue")
    repo_marker = quote(f"Dicklesworthstone/{repo_name}", safe="")
    return (
        "![Stars]"
        f"(https://img.shields.io/badge/stars-{value}-{color_value}"
        "?style=flat-square&logo=github&logoColor=white"
        f"&repo={repo_marker})"
    )


def markdown_escape(value: object) -> str:
    value = html.unescape(str(value)).replace("\n", " ").strip()
    return (
        value.replace("\\", "\\\\")
        .replace("|", "\\|")
        .replace("[", "\\[")
        .replace("]", "\\]")
    )


def display_name(repo_name: str) -> str:
    if repo_name in DISPLAY_NAMES:
        return DISPLAY_NAMES[repo_name]
    return repo_name.replace("_", " ").replace("-", " ").title()


def is_draft(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() == "true"


def load_recent_repos() -> list[dict]:
    try:
        payload = repo_metadata_payload()
    except OSError as exc:
        print(f"warning: could not load repo metadata: {exc}", file=sys.stderr)
        return []

    if payload is None:
        return []

    try:
        repos = decode_json(payload)
    except json.JSONDecodeError as exc:
        print(f"warning: could not decode repo metadata: {exc}", file=sys.stderr)
        return []
    if not isinstance(repos, list):
        print("warning: repo metadata was not a JSON array", file=sys.stderr)
        return []
    repo_items = [repo for repo in repos if isinstance(repo, dict)]
    repo_items.sort(
        key=lambda repo: repo.get("pushedAt") or repo.get("updatedAt") or "",
        reverse=True,
    )
    selected = []
    for repo in repo_items:
        name = repo.get("name", "")
        lowered = name.lower()
        if repo.get("isArchived"):
            continue
        if repo.get("isFork"):
            continue
        if name in RECENT_EXCLUDE:
            continue
        if "12_west" in lowered or "12-west" in lowered or "12west" in lowered:
            continue
        selected.append(repo)
        if len(selected) >= 12:
            break
    return selected


def load_repo_star_counts() -> dict[str, int]:
    try:
        payload = repo_metadata_payload()
    except OSError as exc:
        print(f"warning: could not load repo star counts: {exc}", file=sys.stderr)
        return {}

    if payload is None:
        return {}

    try:
        repos = decode_json(payload)
    except json.JSONDecodeError as exc:
        print(f"warning: could not decode repo star counts: {exc}", file=sys.stderr)
        return {}
    if not isinstance(repos, list):
        print("warning: repo star metadata was not a JSON array", file=sys.stderr)
        return {}
    counts = {}
    for repo in repos:
        if not isinstance(repo, dict):
            continue
        name = repo.get("name")
        stars = repo.get("stargazerCount")
        if isinstance(name, str) and isinstance(stars, int):
            counts[name] = stars
    return counts


def replace_star_badges(text: str, star_counts: dict[str, int]) -> str:
    dynamic_pattern = re.compile(
        r"!\[Stars\]\("
        r"https://img\.shields\.io/github/stars/Dicklesworthstone/"
        r"(?P<repo>[A-Za-z0-9_.-]+)\?(?P<query>[^)]*)\)"
    )

    def dynamic_repl(match: re.Match[str]) -> str:
        repo = match.group("repo")
        stars = star_counts.get(repo)
        if stars is None:
            print(f"warning: no star count found for {repo}; leaving dynamic badge", file=sys.stderr)
            return match.group(0)
        query = dict(parse_qsl(match.group("query"), keep_blank_values=True))
        return static_star_badge(repo, stars, query.get("color", "blue"))

    static_pattern = re.compile(
        r"!\[Stars\]\("
        r"https://img\.shields\.io/badge/stars-[^-)]*-(?P<color>[^?)]*)\?"
        r"(?P<query>[^)]*)\)"
    )

    def static_repl(match: re.Match[str]) -> str:
        query = dict(parse_qsl(match.group("query"), keep_blank_values=True))
        owner_repo = query.get("repo", "")
        prefix = "Dicklesworthstone/"
        if not owner_repo.startswith(prefix):
            return match.group(0)
        repo = owner_repo.removeprefix(prefix)
        stars = star_counts.get(repo)
        if stars is None:
            print(f"warning: no star count found for {repo}; leaving static badge", file=sys.stderr)
            return match.group(0)
        return static_star_badge(repo, stars, match.group("color"))

    text = dynamic_pattern.sub(dynamic_repl, text)
    return static_pattern.sub(static_repl, text)


def build_recent_repos_table() -> str:
    repos = load_recent_repos()
    if not repos:
        return ""
    lines = [
        "| Project | Lang | What it does |",
        "|:--------|:----:|:-------------|",
    ]
    for repo in repos:
        name = repo.get("name")
        url = repo.get("url")
        if not name or not url:
            continue
        lang = repo.get("primaryLanguage") or {}
        if not isinstance(lang, dict):
            lang = {}
        desc = markdown_escape(repo.get("description") or "Recently active public project")
        lines.append(
            "| "
            f"[**{markdown_escape(display_name(name))}**]({url})"
            " | "
            f"{lang_badge(lang.get('name'), lang.get('color'))}"
            " | "
            f"{desc} |"
        )
    return "\n".join(lines)


def unescape_next_payload(text: str) -> str:
    text = text.replace(r"\"", '"')
    return re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), text)


def extract_json_array(text: str, marker: str) -> list[dict]:
    start = text.find(marker)
    if start < 0:
        return []
    i = start + len(marker) - 1
    depth = 0
    in_string = False
    escaped = False
    for j in range(i, len(text)):
        ch = text[j]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
        else:
            if ch == '"':
                in_string = True
            elif ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    try:
                        parsed = decode_json(text[i : j + 1])
                    except json.JSONDecodeError as exc:
                        print(
                            f"warning: could not parse writing metadata after {marker}: {exc}",
                            file=sys.stderr,
                        )
                        return []
                    if not isinstance(parsed, list):
                        return []
                    return parsed
    return []


def fetch_writing_items() -> list[dict]:
    try:
        with urllib.request.urlopen(WRITING_URL, timeout=20) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"warning: could not fetch writing page: {exc}", file=sys.stderr)
        return []

    decoded = unescape_next_payload(raw)
    items = []
    seen = set()
    for marker in ['"featured":[', '"archive":[']:
        for item in extract_json_array(decoded, marker):
            if not isinstance(item, dict):
                continue
            href = item.get("href", "")
            if not href or href in seen:
                continue
            if is_draft(item.get("draft")):
                continue
            seen.add(href)
            items.append(item)
    return items


def build_writing_block() -> str:
    items = fetch_writing_items()
    if not items:
        return ""
    lines = []
    for item in items:
        title_raw = item.get("title")
        href = item.get("href", "")
        if not title_raw or not href:
            continue
        title = markdown_escape(title_raw)
        blurb = markdown_escape(item.get("blurb") or "")
        if href.startswith("/"):
            href = f"{SITE_ROOT}{href}"
        lines.append(f"- **[{title}]({href})** \u2014 {blurb}")
    return "\n".join(lines)


def main() -> None:
    original = README.read_text(encoding="utf-8")
    text = original
    existing_stars_label = existing_badge_message(
        text,
        ["Stars"],
        r"badge/Stars-([^-/]+)-",
        "0+",
    )
    existing_projects = existing_badge_message(
        text,
        ["Repos", "Projects"],
        r"badge/(?:Projects|Repos)-([^-/]+)-",
        "0",
    )
    existing_contributions = existing_badge_message(
        text,
        ["Contributions (1yr)", "Contributions"],
        r"badge/Contributions(?:_\([^)]*\))?-([^-/]+)-",
        "0",
    )
    if existing_contributions == "0":
        existing_contributions = existing_match(
            text,
            r"> \*\*([\d,]+) contributions in the past year\*\*",
            "0",
        )
    existing_followers_label = existing_badge_message(
        text,
        ["Followers"],
        r"badge/Followers-([^-/]+)-",
        "0+",
    )
    existing_x_label = existing_badge_message(
        text,
        ["X Followers", "X_Followers"],
        r"badge/(?:X_Followers|[^-]+_Followers)-([^-/]+)-",
        "0",
    )
    existing_discord_members = existing_match(
        text,
        r"Flywheel_Hub-([\d,]+)_members",
        "0",
    )

    text = replace_line_any(
        text,
        ["![Stars](", "![Stars:"],
        round_badge_line("Stars", env("README_STARS_LABEL", existing_stars_label)),
    )
    text = replace_line_any(
        text,
        ["![Repos](", "![Repos:", "![Projects](", "![Projects:"],
        round_badge_line("Repos", env("OPEN_SOURCE_PROJECTS", existing_projects)),
    )
    text = replace_line_any(
        text,
        [
            "![Contributions](",
            "![Contributions:",
            "![Contributions_(1yr)](",
            "![Contributions_(1yr):",
        ],
        round_badge_line(
            "Contributions (1yr)",
            env("README_CONTRIBUTIONS", env("CONTRIBUTIONS_FMT", existing_contributions)),
            alt_label="Contributions",
        ),
    )
    text = replace_line_any(
        text,
        ["![Followers](", "![Followers:"],
        round_badge_line("Followers", env("README_FOLLOWERS_LABEL", existing_followers_label)),
    )
    text = replace_line_any(
        text,
        ["![X](", "![X:", "![X_Followers](", "![X_Followers:"],
        round_badge_line(
            "X Followers",
            env("X_FOLLOWERS_LABEL", existing_x_label),
            logo="x",
            alt_label="X",
        ),
    )
    discord_members = env("DISCORD_MEMBERS_FMT", existing_discord_members)
    text = replace_line_any(
        text,
        ["[![Discord]("],
        discord_badge_line(discord_members),
    )

    contribution_text = env("README_CONTRIBUTIONS", existing_contributions)
    text = re.sub(
        r"> \*\*[\d,]+ contributions in the past year\*\*",
        f"> **{contribution_text} contributions in the past year**",
        text,
        count=1,
    )

    open_source_projects = env("OPEN_SOURCE_PROJECTS", existing_projects)
    stats_sentence = (
        f"- {env('README_STARS_LABEL', existing_stars_label)} GitHub stars, "
        f"{env('README_FOLLOWERS_LABEL', existing_followers_label)} GitHub followers, "
        f"{open_source_projects} open-source projects, "
        f"{env('X_FOLLOWERS_LABEL', existing_x_label)} X followers"
    )
    text = re.sub(
        r"- [\d,.kK+]+ GitHub stars, [\d,.kK+]+ GitHub followers, "
        r"\d+ open-source projects, [\d,.kK+]+ X followers",
        stats_sentence,
        text,
        count=1,
    )

    text = re.sub(
        r"Next\.js 16, React Three Fiber, and GSAP\. \d+ project showcase\.",
        f"Next.js 16, React Three Fiber, and GSAP. {open_source_projects} project showcase.",
        text,
        count=1,
    )

    text = re.sub(
        r"~[\d,]+ members",
        f"~{discord_members} members",
        text,
    )

    text = text.replace("label=\u2b50", "label=%E2%AD%90")
    star_counts = load_repo_star_counts()
    if star_counts:
        text = replace_star_badges(text, star_counts)

    recent_block = build_recent_repos_table()
    if recent_block:
        start = "<!-- BEGIN AUTO-BUILDING-NOW -->"
        end = "<!-- END AUTO-BUILDING-NOW -->"
        if start in text:
            text = between_markers(text, start, end, recent_block)
        else:
            text = replace_section_range(
                text,
                r"## What I'm Building Now\n\n",
                r"### Live Demos",
                f"{start}\n{recent_block}\n{end}",
            )

    writing_block = build_writing_block()
    if writing_block:
        start = "<!-- BEGIN AUTO-WRITING -->"
        end = "<!-- END AUTO-WRITING -->"
        if start in text:
            text = between_markers(text, start, end, writing_block)
        else:
            text = replace_section_range(
                text,
                r"Selected essays from \[jeffreyemanuel\.com/writing\]"
                r"\(https://www\.jeffreyemanuel\.com/writing\):\n\n",
                r"---\n\n## GitHub Activity",
                f"{start}\n{writing_block}\n{end}",
            )

    if text != original:
        README.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
