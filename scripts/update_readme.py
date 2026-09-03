#!/usr/bin/env python3
"""Refresh mechanical README.md sections from live GitHub/site data."""

from __future__ import annotations

import html
import http.client
import json
import math
import os
import re
import stat
import sys
import tempfile
import urllib.request
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, quote, urlencode, urljoin, urlparse

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
WRITING_URL = os.environ.get("WRITING_URL", "https://www.jeffreyemanuel.com/writing")
SITE_ROOT = "https://www.jeffreyemanuel.com"
JSON_DECODER = json.JSONDecoder()
MAX_WRITING_BYTES = 4 * 1024 * 1024


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
    "aadc": "AADC",
    "acip": "ACIP",
    "asimposium.org": "ASImposium",
    "asupersync": "Asupersync",
    "asupersync_ansi_c": "Asupersync ANSI C",
    "atp": "ATP",
    "classic-patents.com": "Classic Patents",
    "beads_viewer_rust": "Beads Viewer Rust",
    "coding_agent_session_search": "CASS",
    "cass_memory_system": "CASS Memory",
    "destructive_command_guard": "DCG",
    "dwarf_fortress_mcp": "Dwarf Fortress MCP",
    "doodlestein_self_releaser": "Doodlestein Self-Releaser",
    "ees": "EES",
    "eidetic_engine_cli": "Eidetic Engine CLI",
    "fastapi_rust": "FastAPI Rust",
    "fastmcp_rust": "FastMCP Rust",
    "franken_agent_detection": "Franken Agent Detection",
    "franken_drone_geometry_reconstruction": "Franken Drone Geometry Reconstruction",
    "franken_engine": "FrankenEngine",
    "franken_lean": "FrankenLean",
    "franken_manim": "FrankenManim",
    "franken_markdown": "FrankenMarkdown",
    "franken_networkx": "FrankenNetworkX",
    "franken_node": "FrankenNode",
    "franken_numpy": "FrankenNumPy",
    "franken_overlap": "FrankenOverlap",
    "franken_ocr": "FrankenOCR",
    "franken_snowflake": "FrankenSnowflake",
    "franken_surveillance_system": "Franken Surveillance System",
    "franken_tts": "FrankenTTS",
    "franken_whisper": "FrankenWhisper",
    "frankenfs": "FrankenFS",
    "frankengraphdb": "FrankenGraphDB",
    "frankengit": "FrankenGit",
    "frankenjax": "FrankenJAX",
    "frankenlibc": "FrankenLibC",
    "frankenmermaid": "FrankenMermaid",
    "frankenpandas": "FrankenPandas",
    "frankenredis": "FrankenRedis",
    "frankenscipy": "FrankenSciPy",
    "frankensearch": "FrankenSearch",
    "frankensim": "FrankenSim",
    "frankensqlite": "FrankenSQLite",
    "frankensympy": "FrankenSymPy",
    "frankenterm": "FrankenTerm",
    "frankentorch": "FrankenTorch",
    "frankentui": "FrankenTUI",
    "giil": "GIIL",
    "llm-tournament": "LLM Tournament",
    "mcp_agent_mail": "MCP Agent Mail",
    "mcp_agent_mail_rust": "MCP Agent Mail Rust",
    "ntm": "NTM",
    "opentui_rust": "OpenTUI Rust",
    "pi_agent_rust": "Pi Agent Rust",
    "repo_updater": "RU",
    "slb": "SLB",
    "sqlmodel_rust": "SQLModel Rust",
    "storage_ballast_helper": "Storage Ballast Helper",
    "toon_rust": "TOON Rust",
    "ultimate_bug_scanner": "UBS",
    "vibe_cockpit": "Vibe Cockpit",
    "xf": "XF",
}

# Public-facing descriptions for repositories that regularly appear in the
# activity table. GitHub repository descriptions optimize for search and often
# read poorly when copied into a profile. Keep this small map manually edited;
# unknown repositories still use their live GitHub descriptions.
RECENT_DESCRIPTION_OVERRIDES = {
    "asimposium.org": (
        "Public scientific ledger where human-sponsored AI agents submit, review, "
        "and challenge work in mathematics and physics."
    ),
    "classic-patents.com": (
        "Digital museum of landmark patents with corrected transcripts, "
        "plain-English engineering notes, and interactive simulations."
    ),
    "franken_lean": (
        "Rust implementation of the Lean 4 toolchain with `.olean`, C ABI, LSP, and "
        "CLI compatibility; deterministic parallelism; declaration-level "
        "incrementality; and a dual-engine kernel capped at 12 KLOC."
    ),
    "franken_manim": (
        "Deterministic Rust implementation of 3b1b's Manim with native TeX "
        "typesetting, an analytic Bézier renderer, bit-reproducible output, and "
        "source compatibility with manimlib scenes. FFmpeg is its only external "
        "tool."
    ),
    "frankengraphdb": (
        "Rust property-graph database with MVCC, time travel, branches, "
        "WCO/factorized execution, incremental maintenance, and fountain-coded "
        "replication."
    ),
    "frankengit": (
        "Git-compatible forge for human and coding-agent workflows, with "
        "verifiable recovery, self-hosting, and an immutable decision stream."
    ),
    "frankenmermaid": (
        "Rust diagram engine with 15 layout algorithms and deterministic SVG, "
        "Canvas, terminal, and WASM rendering."
    ),
    "frankensim": (
        "Rust geometry, simulation, optimization, and rendering workspace with "
        "contract-backed kernels."
    ),
    "frankensqlite": (
        "Rust implementation of SQLite with page-level MVCC concurrent-writer "
        "support and RaptorQ durability components."
    ),
    "frankenterm": (
        "WezTerm-based terminal for AI-agent swarms, with pane capture, "
        "state-machine detection, and a JSON control API."
    ),
    "frankentorch": (
        "Clean-room Rust implementation of PyTorch with deterministic autograd, "
        "compatibility modes, differential tests, and RaptorQ-backed durability."
    ),
    "pi_agent_rust": (
        "Rust coding-agent CLI with sub-100ms startup, eight built-in tools, "
        "session branching, and a roughly 15 MB binary."
    ),
}

# Article titles and order come from the live writing page. These blurbs are
# deliberately written for the compact profile format and keyed by stable path.
WRITING_BLURB_OVERRIDES = {
    "/writing/wills-and-estate-planning": (
        "A Claude Code and Codex skill that turns one weekend and about $120 into "
        "a structured estate-planning intake package for attorney review."
    ),
    "/writing/slack-mattermost-migration": (
        "Two paired skills migrate Slack data to self-hosted Mattermost with a "
        "readiness gate, named rollback owner, and roughly 99% lower ongoing cost."
    ),
    "/writing/overprompting": (
        "How excessive constraints hurt model output, with a two-phase prompting "
        "method that leaves more room for the model to reason."
    ),
    "/writing/hoeffdings_d_explainer": (
        "A guide to Hoeffding's D, a nonparametric dependence measure that detects "
        "nonlinear relationships missed by Pearson and Spearman correlation."
    ),
    "/writing/barra-factor-model": (
        "How Barra-style factor models can distort incentives, encourage crowding, "
        "and hide shared risk at multi-manager funds."
    ),
    "/writing/raptorq": (
        "How RaptorQ (RFC 6330) turns a file into interchangeable repair packets "
        "with about 0.02% overhead."
    ),
    "/writing/cmaes_explainer": (
        "An interactive explanation of CMA-ES and its search of high-dimensional, "
        "nonconvex objective functions without gradients."
    ),
    "/writing/the_short_case_for_nvda": (
        "The 12,000-word case that DeepSeek, inference economics, and GPU supply "
        "could pressure Nvidia's valuation and the AI capital-spending cycle."
    ),
    "/writing/the_most_impressive_prediction_of_all_time": (
        "A close reading of Pyotr Durnovo's 1914 memorandum, which predicted the "
        "World War I alliances and a Russian revolution."
    ),
    "/writing/hermann_grassmann_nature_of_abstractions": (
        "How Hermann Grassmann developed the exterior product decades before "
        "mathematicians recognized its value."
    ),
    "/writing/bio_inspired_architecture": (
        "A transformer architecture with metabolically regulated weights, "
        "synaptic fatigue, and structural plasticity."
    ),
    "/writing/model_guided_math": (
        "Eleven mathematical approaches to transformer alternatives, including "
        "Lie groups, p-adic numbers, and tropical geometry."
    ),
    "/writing/bakery_algorithm": (
        "A visual Python implementation of Lamport's fair mutual-exclusion "
        "algorithm for systems without atomic hardware primitives."
    ),
    "/writing/llm_introspective_compression": (
        "A proposal to let language models compress and restore their own reasoning "
        "state for backtracking and reinforcement learning."
    ),
    "/writing/llm_multi_round_coding_tournament": (
        "A framework in which multiple models critique and revise coding solutions "
        "across several rounds to escape local optima."
    ),
    "/writing/making_complex_code_changes_with_cc": (
        "A plan-first method for complex coding-agent tasks that separates reasoning "
        "from implementation and allocates more tokens to design."
    ),
    "/writing/protecting_against_prompt_injection": (
        "A history of prompt-injection techniques and a proposal for external "
        "monitor models that enforce policy."
    ),
    "/writing/dr_gpt_empowering_your_healthcare_with_ai": (
        "A workflow for combining scattered medical records into one dossier so "
        "patients can review missed diagnoses and drug interactions with clinicians."
    ),
    "/writing/tax_gpt_using_ai_for_tax_prep": (
        "A method for splitting tax returns into model-sized chunks to find possible "
        "deductions and errors before professional review."
    ),
    "/writing/making_of_the_mindmap_generator": (
        "The nonlinear exploration architecture used to extract hierarchical "
        "structure from long documents while controlling hallucinations."
    ),
    "/writing/ppp_loan_fraud_analysis": (
        "A network-analysis reconstruction of PPP loan fraud patterns and the simple "
        "checks that could have flagged billions in suspicious loans."
    ),
    "/writing/what_i_learned_making_the_python_backend_for_yto": (
        "A technical retrospective on a FastAPI, SQLModel, and Pydantic backend for "
        "Whisper transcription under concurrent load."
    ),
    "/writing/intro_post_discussing_blogging_system": (
        "How the Next.js and Tailwind blog uses static generation, responsive "
        "layouts, and fast page loads."
    ),
    "/writing/some_thoughts_on_ai_alignment": (
        "A proposal for external monitor models that apply policy to a primary "
        "model's output, modeled on a criminal-justice system."
    ),
    "/writing/nextjs_github_blogging_system": (
        "How the open-source blog uses GitHub as a headless CMS, Git for version "
        "history, and static generation for page speed."
    ),
}

RECENT_EXCLUDE = {
    "dicklesworthstone",
    "homebrew-tap",
    "scoop-bucket",
}
GITHUB_REPO_NAME = re.compile(r"^[A-Za-z0-9_.-]+$")
HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def replace_line_any(text: str, prefixes: list[str], replacement: str) -> str:
    pattern = re.compile(
        r"^(?:" + "|".join(re.escape(prefix) for prefix in prefixes) + r").*$",
        re.MULTILINE,
    )
    matches = list(pattern.finditer(text))
    if len(matches) != 1:
        raise SystemExit(
            "Expected exactly one README line starting with one of: "
            + ", ".join(prefixes)
        )
    return pattern.sub(lambda _match: replacement, text)


def replace_pattern_exact(
    text: str,
    pattern: str,
    replacement: str,
    *,
    expected: int | None = 1,
) -> str:
    """Replace schema-bound matches; ``None`` means one or more occurrences."""
    compiled = re.compile(pattern, re.MULTILINE)
    matches = list(compiled.finditer(text))
    valid_count = bool(matches) if expected is None else len(matches) == expected
    if not valid_count:
        expectation = "at least 1" if expected is None else str(expected)
        raise SystemExit(
            f"Expected {expectation} README match(es), found {len(matches)}: {pattern}"
        )
    return compiled.sub(lambda _match: replacement, text)


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
        message = params.get("message")
        if params.get("label") in labels and isinstance(message, str) and message:
            return message
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


def recent_activity_payload() -> str | None:
    content = env("RECENT_ACTIVITY_JSON_CONTENT")
    if content:
        return content

    path = env("RECENT_ACTIVITY_JSON")
    if not path:
        return None
    return Path(path).read_text(encoding="utf-8")


def between_markers(text: str, start: str, end: str, block: str) -> str:
    if text.count(start) != 1 or text.count(end) != 1:
        raise SystemExit(f"Expected one README marker pair: {start} / {end}")
    marker_pattern = re.compile(
        rf"{re.escape(start)}\n.*?\n{re.escape(end)}",
        re.DOTALL,
    )
    replacement = f"{start}\n{block.rstrip()}\n{end}"
    updated, count = marker_pattern.subn(replacement, text, count=1)
    if count != 1:
        raise SystemExit(
            f"Could not locate complete README marker pair: {start} / {end}"
        )
    return updated


def replace_section_range(
    text: str, start_pattern: str, end_pattern: str, replacement: str
) -> str:
    start_matches = list(re.finditer(start_pattern, text, re.MULTILINE))
    end_matches = list(re.finditer(end_pattern, text, re.MULTILINE))
    if len(start_matches) != 1 or len(end_matches) != 1:
        raise SystemExit(
            "Expected exactly one README section boundary pair for replacement"
        )
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


def replace_generated_section(
    text: str,
    start: str,
    end: str,
    block: str,
    legacy_start_pattern: str,
    legacy_end_pattern: str,
) -> str:
    """Refresh a marked block, migrating only when neither marker exists."""
    if start in text or end in text:
        return between_markers(text, start, end, block)
    return replace_section_range(
        text,
        legacy_start_pattern,
        legacy_end_pattern,
        f"{start}\n{block}\n{end}",
    )


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
    name = language if isinstance(language, str) and language else "Code"
    logo = LANG_LOGOS.get(name, "")
    supplied_color = (
        color if isinstance(color, str) and HEX_COLOR.fullmatch(color) else None
    )
    color_value = (supplied_color or LANG_COLORS.get(name) or "#2b2b2b").lstrip("#")
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
    value = html.unescape(str(value))
    value = "".join(" " if ord(character) < 32 else character for character in value)
    value = value.strip()
    escaped = (
        value.replace("\\", "\\\\")
        .replace("|", "\\|")
        .replace("[", "\\[")
        .replace("]", "\\]")
    )
    return html.escape(escaped, quote=False)


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


def is_nonnegative_number(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and value >= 0
    )


def parse_activity_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed


def load_recent_repos() -> list[dict[str, Any]]:
    try:
        payload = recent_activity_payload()
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
    repo_items = []
    seen_names: set[str] = set()
    for repo in repos:
        if not isinstance(repo, dict):
            print("warning: recent activity entry was not an object", file=sys.stderr)
            return []
        activity = repo.get("recentActivity")
        if not isinstance(activity, dict):
            print("warning: recent activity entry omitted metrics", file=sys.stderr)
            return []
        name = repo.get("name")
        url = repo.get("url")
        description = repo.get("description")
        language = repo.get("primaryLanguage")
        language_name = language.get("name") if isinstance(language, dict) else None
        language_color = language.get("color") if isinstance(language, dict) else None
        integer_fields = (
            "commitCount",
            "additions",
            "deletions",
            "changedLines",
        )
        window_days = activity.get("windowDays")
        window_start = activity.get("windowStart")
        window_end = activity.get("windowEnd")
        window_start_at = parse_activity_timestamp(window_start)
        window_end_at = parse_activity_timestamp(window_end)
        integer_values = [activity.get(field) for field in integer_fields]
        if (
            not isinstance(name, str)
            or not name
            or GITHUB_REPO_NAME.fullmatch(name) is None
            or name.lower() in seen_names
            or not isinstance(url, str)
            or url != f"https://github.com/Dicklesworthstone/{name}"
            or repo.get("isArchived") is not False
            or repo.get("isFork") is not False
            or (description is not None and not isinstance(description, str))
            or (language is not None and not isinstance(language, dict))
            or (
                isinstance(language, dict)
                and (
                    not isinstance(language_name, str)
                    or not language_name
                    or (
                        language_color is not None
                        and (
                            not isinstance(language_color, str)
                            or HEX_COLOR.fullmatch(language_color) is None
                        )
                    )
                )
            )
            or not isinstance(window_days, int)
            or isinstance(window_days, bool)
            or window_days < 1
            or window_start_at is None
            or window_end_at is None
            or not is_nonnegative_number(activity.get("score"))
            or any(
                not isinstance(value, int) or isinstance(value, bool) or value < 0
                for value in integer_values
            )
            or not is_nonnegative_number(activity.get("commitCount"))
            or activity.get("commitCount") == 0
        ):
            print("warning: recent activity entry was malformed", file=sys.stderr)
            return []
        changed_lines = activity["changedLines"]
        if (
            changed_lines != activity["additions"] + activity["deletions"]
            or (window_end_at - window_start_at).total_seconds() != window_days * 86_400
            or not math.isclose(
                activity["score"],
                activity["commitCount"] * math.log2(2 + changed_lines),
                rel_tol=0,
                abs_tol=0.000001,
            )
        ):
            print("warning: recent activity metrics were inconsistent", file=sys.stderr)
            return []
        seen_names.add(name.lower())
        repo_items.append(repo)
    repo_items.sort(
        key=lambda repo: (
            repo["recentActivity"].get("score", 0),
            repo["recentActivity"].get("commitCount", 0),
            repo["recentActivity"].get("changedLines", 0),
        ),
        reverse=True,
    )
    selected = []
    for repo in repo_items:
        name = repo.get("name", "")
        lowered = name.lower()
        if lowered in RECENT_EXCLUDE:
            print("warning: recent activity included an excluded repo", file=sys.stderr)
            return []
        if "12_west" in lowered or "12-west" in lowered or "12west" in lowered:
            print("warning: recent activity included an excluded repo", file=sys.stderr)
            return []
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
    counts: dict[str, int] = {}
    seen_names: set[str] = set()
    for repo in repos:
        if not isinstance(repo, dict):
            print("warning: repo star metadata entry was malformed", file=sys.stderr)
            return {}
        name = repo.get("name")
        stars = repo.get("stargazerCount")
        if (
            not isinstance(name, str)
            or not name
            or GITHUB_REPO_NAME.fullmatch(name) is None
            or name.lower() in seen_names
            or not isinstance(stars, int)
            or isinstance(stars, bool)
            or stars < 0
        ):
            print("warning: repo star metadata entry was malformed", file=sys.stderr)
            return {}
        seen_names.add(name.lower())
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
            print(
                f"warning: no star count found for {repo}; leaving dynamic badge",
                file=sys.stderr,
            )
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
            print(
                f"warning: no star count found for {repo}; leaving static badge",
                file=sys.stderr,
            )
            return match.group(0)
        return static_star_badge(repo, stars, match.group("color"))

    text = dynamic_pattern.sub(dynamic_repl, text)
    return static_pattern.sub(static_repl, text)


def build_recent_repos_table() -> str:
    repos = load_recent_repos()
    if not repos:
        return ""
    windows = {
        (
            repo["recentActivity"]["windowDays"],
            repo["recentActivity"]["windowStart"],
            repo["recentActivity"]["windowEnd"],
        )
        for repo in repos
    }
    if len(windows) != 1:
        print("warning: recent activity windows do not match", file=sys.stderr)
        return ""
    window_days, _, _ = windows.pop()
    lines = [
        (
            f"*Ranked by live default-branch activity over the trailing {window_days} "
            "days: commits × log₂(2 + aggregate changed lines). Line totals compare "
            "the branch at the start and end of the window.*"
        ),
        "",
        f"| Project | Lang | {window_days}-day activity | What it does |",
        "|:--------|:----:|:----------------|:-------------|",
    ]
    for repo in repos:
        name = repo.get("name")
        url = repo.get("url")
        if not name or not url:
            continue
        lang = repo.get("primaryLanguage") or {}
        if not isinstance(lang, dict):
            lang = {}
        activity = repo.get("recentActivity") or {}
        commits = int(activity.get("commitCount") or 0)
        additions = int(activity.get("additions") or 0)
        deletions = int(activity.get("deletions") or 0)
        commit_label = "commit" if commits == 1 else "commits"
        source_description = (
            repo.get("description") or "Recently active public project"
        )
        desc = markdown_escape(
            RECENT_DESCRIPTION_OVERRIDES.get(name, source_description)
        )
        lines.append(
            "| "
            f"[**{markdown_escape(display_name(name))}**]({url})"
            " | "
            f"{lang_badge(lang.get('name'), lang.get('color'))}"
            " | "
            f"{commits:,} {commit_label}<br>+{additions:,} / −{deletions:,} lines"
            " | "
            f"{desc} |"
        )
    return "\n".join(lines)


def unescape_next_payload(text: str) -> str:
    text = text.replace(r"\"", '"')
    return re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), text)


def extract_json_array(text: str, marker: str) -> list[dict[str, Any]]:
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


class WritingPageParser(HTMLParser):
    """Extract article-card text from the server-rendered writing page."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.items: list[dict[str, str]] = []
        self.href: str | None = None
        self.in_article = False
        self.heading_tag: str | None = None
        self.in_blurb = False
        self.title_parts: list[str] = []
        self.blurb_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "a":
            href = attributes.get("href")
            if isinstance(href, str) and "/writing/" in href:
                self.href = href
                self.in_article = False
                self.heading_tag = None
                self.in_blurb = False
                self.title_parts = []
                self.blurb_parts = []
        elif self.href is not None and tag == "article":
            self.in_article = True
        elif (
            self.in_article
            and self.heading_tag is None
            and tag
            in {
                "h1",
                "h2",
                "h3",
                "h4",
                "h5",
                "h6",
            }
        ):
            self.heading_tag = tag
        elif self.in_article and tag == "p" and not self.blurb_parts:
            self.in_blurb = True

    def handle_endtag(self, tag: str) -> None:
        if tag == self.heading_tag:
            self.heading_tag = None
        elif tag == "p":
            self.in_blurb = False
        elif tag == "article":
            self.in_article = False
        elif tag == "a" and self.href is not None:
            title = "".join(self.title_parts).strip()
            blurb = "".join(self.blurb_parts).strip()
            if title:
                self.items.append({"title": title, "href": self.href, "blurb": blurb})
            self.href = None
            self.in_article = False
            self.heading_tag = None
            self.in_blurb = False

    def handle_data(self, data: str) -> None:
        if self.heading_tag is not None:
            self.title_parts.append(data)
        elif self.in_blurb:
            self.blurb_parts.append(data)


def extract_rendered_writing_items(raw: str) -> list[dict[str, Any]]:
    parser = WritingPageParser()
    parser.feed(raw)
    parser.close()

    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in parser.items:
        href = normalize_writing_href(item.get("href"))
        if href is None or href in seen:
            continue
        seen.add(href)
        normalized: dict[str, Any] = dict(item)
        normalized["href"] = href
        items.append(normalized)
    return items


def fetch_writing_items() -> list[dict[str, Any]]:
    try:
        parsed_url = urlparse(WRITING_URL)
    except ValueError:
        print("warning: writing URL was malformed", file=sys.stderr)
        return []
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        print("warning: writing URL must use HTTP or HTTPS", file=sys.stderr)
        return []
    try:
        with urllib.request.urlopen(WRITING_URL, timeout=20) as response:
            payload = response.read(MAX_WRITING_BYTES + 1)
    except (OSError, http.client.HTTPException) as exc:
        print(f"warning: could not fetch writing page: {exc}", file=sys.stderr)
        return []
    if len(payload) > MAX_WRITING_BYTES:
        print("warning: writing page exceeded the response size limit", file=sys.stderr)
        return []
    raw = payload.decode("utf-8", errors="replace")

    rendered_items = extract_rendered_writing_items(raw)
    # Older deployments exposed explicit metadata arrays in the Next.js
    # hydration payload. Retain that path as a compatibility source, and merge
    # it with rendered cards: streaming or partially cached HTML can contain
    # only the first rendered card even though the hydration data is complete.
    decoded = unescape_next_payload(raw)
    items = list(rendered_items)
    seen = {item["href"] for item in rendered_items}
    for marker in ['"featured":[', '"archive":[']:
        for item in extract_json_array(decoded, marker):
            if not isinstance(item, dict):
                continue
            href = normalize_writing_href(item.get("href"))
            if href is None or href in seen:
                continue
            if is_draft(item.get("draft")):
                continue
            seen.add(href)
            normalized = dict(item)
            normalized["href"] = href
            items.append(normalized)
    return items


def normalize_writing_href(value: object) -> str | None:
    """Accept only same-site HTTP(S) links and encode Markdown delimiters."""
    if not isinstance(value, str) or not value or any(ord(ch) < 32 for ch in value):
        return None
    try:
        absolute = urljoin(SITE_ROOT, value)
        parsed = urlparse(absolute)
        hostname = parsed.hostname
    except ValueError:
        return None
    if (
        parsed.scheme not in {"http", "https"}
        or (hostname or "").lower()
        not in {"jeffreyemanuel.com", "www.jeffreyemanuel.com"}
        or parsed.username is not None
        or parsed.password is not None
    ):
        return None
    return quote(absolute, safe=":/?#[]@!$&'*+,;=%~._-")


def build_writing_block() -> str:
    items = fetch_writing_items()
    if not items:
        return ""
    lines = []
    for item in items:
        title_raw = item.get("title")
        href = item.get("href", "")
        blurb_raw = item.get("blurb")
        if (
            not isinstance(title_raw, str)
            or not title_raw.strip()
            or not isinstance(href, str)
            or not href
            or (blurb_raw is not None and not isinstance(blurb_raw, str))
        ):
            print("warning: writing metadata item was malformed", file=sys.stderr)
            return ""
        title = markdown_escape(title_raw)
        path = urlparse(href).path.rstrip("/") or "/"
        blurb = markdown_escape(
            WRITING_BLURB_OVERRIDES.get(path, blurb_raw or "")
        )
        line = f"- **[{title}]({href})**"
        if blurb:
            line += f": {blurb}"
        lines.append(line)
    return "\n".join(lines)


def write_atomically(path: Path, content: str) -> None:
    """Replace a text artifact only after its complete contents are durable."""
    try:
        mode = stat.S_IMODE(path.stat().st_mode)
    except FileNotFoundError:
        mode = 0o644
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            os.fchmod(handle.fileno(), mode)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


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
            r"> \*\*([\d,]+) contributions in the past year\.?\*\*",
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
        round_badge_line(
            "Projects", env("OPEN_SOURCE_PROJECTS", existing_projects)
        ),
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
            env(
                "README_CONTRIBUTIONS", env("CONTRIBUTIONS_FMT", existing_contributions)
            ),
            alt_label="Contributions",
        ),
    )
    text = replace_line_any(
        text,
        ["![Followers](", "![Followers:"],
        round_badge_line(
            "Followers", env("README_FOLLOWERS_LABEL", existing_followers_label)
        ),
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
    text = replace_pattern_exact(
        text,
        r"> \*\*[\d,]+ contributions in the past year\.?\*\*",
        f"> **{contribution_text} contributions in the past year.**",
    )

    open_source_projects = env("OPEN_SOURCE_PROJECTS", existing_projects)
    stats_sentence = (
        f"- {env('README_STARS_LABEL', existing_stars_label)} GitHub stars, "
        f"{env('README_FOLLOWERS_LABEL', existing_followers_label)} GitHub followers, "
        f"{open_source_projects} open-source projects, "
        f"{env('X_FOLLOWERS_LABEL', existing_x_label)} X followers"
    )
    text = replace_pattern_exact(
        text,
        r"- [\d,.kKmM+]+ GitHub stars, [\d,.kKmM+]+ GitHub followers, "
        r"\d+ open-source projects, [\d,.kKmM+]+ X followers",
        stats_sentence,
    )

    text = replace_pattern_exact(
        text,
        r"Next\.js 16, React Three Fiber, and GSAP\. "
        r"(?:\d+ project showcase|(?:A )?showcase of \d+ projects|"
        r"Portfolio for \d+ open-source projects)\.",
        f"Next.js 16, React Three Fiber, and GSAP. "
        f"Portfolio for {open_source_projects} open-source projects.",
    )

    text = replace_pattern_exact(
        text,
        r"~[\d,]+ members",
        f"~{discord_members} members",
        expected=None,
    )

    text = text.replace("label=\u2b50", "label=%E2%AD%90")
    star_counts = load_repo_star_counts()
    if star_counts:
        text = replace_star_badges(text, star_counts)

    recent_block = build_recent_repos_table()
    if recent_block:
        start = "<!-- BEGIN AUTO-BUILDING-NOW -->"
        end = "<!-- END AUTO-BUILDING-NOW -->"
        text = replace_generated_section(
            text,
            start,
            end,
            recent_block,
            r"## What I'm Building Now\n\n",
            r"### Live Demos",
        )

    writing_block = build_writing_block()
    if writing_block:
        start = "<!-- BEGIN AUTO-WRITING -->"
        end = "<!-- END AUTO-WRITING -->"
        text = replace_generated_section(
            text,
            start,
            end,
            writing_block,
            r"Selected essays from \[jeffreyemanuel\.com/writing\]"
            r"\(https://www\.jeffreyemanuel\.com/writing\):\n\n",
            r"---\n\n## GitHub Activity",
        )

    if text != original:
        write_atomically(README, text)


if __name__ == "__main__":
    main()
