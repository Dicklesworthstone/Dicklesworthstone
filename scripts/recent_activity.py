#!/usr/bin/env python3
"""Rank public repositories by recent, live default-branch Git activity.

The profile's "What I'm Building Now" section should reflect substantive work,
not whichever repository most recently received a maintenance push. This
script joins metadata from ``gh repo list`` to clones below ``~/projects``,
fetches every candidate's current default branch, and measures commit count
plus the aggregate line diff over one fixed snapshot window.

Missing local clones are measured in an isolated temporary bare clone. The
command fails rather than emitting a partial ranking if any candidate cannot
be fetched or measured, so the README generator preserves the last complete
section.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

OWNER = "Dicklesworthstone"
DEFAULT_WINDOW_DAYS = 14
DEFAULT_LIMIT = 12
MAX_WORKERS = 6
MAX_TEMPORARY_CLONES = 5
EXCLUDED = {"dicklesworthstone", "homebrew-tap", "scoop-bucket"}
GITHUB_COMPONENT = re.compile(r"^[A-Za-z0-9_.-]+$")


def git(repo: Path, *args: str) -> str:
    """Run Git without exposing remote URLs in diagnostics."""
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0", "LC_ALL": "C"},
        timeout=180,
    )
    return result.stdout


def parse_github_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(timezone.utc)


def is_excluded(name: str) -> bool:
    lowered = name.lower()
    return (
        lowered in EXCLUDED
        or "12_west" in lowered
        or "12-west" in lowered
        or "12west" in lowered
    )


def is_safe_github_component(value: str) -> bool:
    return value not in {".", ".."} and GITHUB_COMPONENT.fullmatch(value) is not None


def recent_candidates(repos: object, since: datetime) -> dict[str, dict[str, Any]]:
    if not isinstance(repos, list):
        raise TypeError("repository metadata must be a JSON array")
    selected: dict[str, dict[str, Any]] = {}
    seen_names: set[str] = set()
    for repo in repos:
        if not isinstance(repo, dict):
            raise TypeError("repository metadata entry must be an object")
        name = repo.get("name")
        if not isinstance(name, str) or not is_safe_github_component(name):
            raise TypeError("repository metadata contains an invalid name")
        lowered = name.lower()
        if lowered in seen_names:
            raise TypeError("repository metadata contains a duplicate name")
        seen_names.add(lowered)
        if not isinstance(repo.get("isArchived"), bool) or not isinstance(
            repo.get("isFork"), bool
        ):
            raise TypeError("repository metadata contains invalid visibility flags")
        pushed_value = repo.get("pushedAt")
        pushed_at = parse_github_timestamp(pushed_value)
        if pushed_value is not None and pushed_at is None:
            raise TypeError("repository metadata contains an invalid push timestamp")
        if repo["isArchived"] or repo["isFork"] or is_excluded(name):
            continue
        if pushed_at is None or pushed_at < since:
            continue
        selected[name] = repo
    return selected


def github_remote_repo_name(remote: str, owner: str) -> str | None:
    """Parse an exact github.com origin in URL or scp-style SSH syntax."""
    remote = remote.strip()
    scp_match = re.fullmatch(
        r"(?:[^@\s/:]+@)?github\.com:(?P<path>[^?#]+)",
        remote,
        flags=re.IGNORECASE,
    )
    if scp_match:
        remote_path = scp_match.group("path")
    else:
        try:
            parsed = urlparse(remote)
            hostname = parsed.hostname
        except ValueError:
            return None
        if (
            parsed.scheme.lower() not in {"git", "http", "https", "ssh"}
            or (hostname or "").lower() != "github.com"
            or parsed.query
            or parsed.fragment
        ):
            return None
        remote_path = parsed.path

    parts = remote_path.strip("/").split("/")
    if len(parts) != 2 or parts[0].casefold() != owner.casefold():
        return None
    name = parts[1]
    if name.lower().endswith(".git"):
        name = name[:-4]
    return name if is_safe_github_component(name) else None


def remote_repo_name(repo: Path, owner: str) -> str | None:
    """Return the owner's GitHub repository name without printing its URL."""
    try:
        remote = git(repo, "config", "--get", "remote.origin.url")
    except (subprocess.SubprocessError, OSError):
        return None
    return github_remote_repo_name(remote, owner)


def discover_clones(root: Path, owner: str, wanted: set[str]) -> dict[str, Path]:
    try:
        children = list(root.iterdir())
    except OSError as exc:
        raise RuntimeError(f"could not scan projects root {root}: {exc}") from exc

    wanted_lower = {name.lower(): name for name in wanted}
    clones: dict[str, Path] = {}
    for child in children:
        if not child.is_dir() or not (child / ".git").exists():
            continue
        remote_name = remote_repo_name(child, owner)
        canonical = wanted_lower.get((remote_name or "").lower())
        if canonical and canonical not in clones:
            clones[canonical] = child
    return clones


def metadata_default_branch(repo: dict[str, Any]) -> str:
    branch = repo.get("defaultBranchRef")
    name = branch.get("name") if isinstance(branch, dict) else None
    if not isinstance(name, str) or not name:
        raise RuntimeError("GitHub metadata omitted the default branch")
    return name


def fetch_default_branch(repo: Path, branch: str) -> str:
    """Fetch and return the current remote-tracking default-branch ref."""
    git(repo, "check-ref-format", "--branch", branch)
    remote_ref = f"refs/remotes/origin/{branch}"
    for attempt in range(1, 4):
        shallow = git(repo, "rev-parse", "--is-shallow-repository").strip()
        if shallow not in {"true", "false"}:
            raise RuntimeError("Git returned an invalid shallow-repository status")
        fetch_args = ["fetch", "--quiet", "--no-tags"]
        if shallow == "true":
            # Otherwise a window that predates the shallow boundary is diffed
            # against an empty tree and looks much larger than it really is.
            fetch_args.append("--unshallow")
        fetch_args.extend(("origin", f"+refs/heads/{branch}:{remote_ref}"))
        try:
            git(repo, *fetch_args)
            break
        except (subprocess.SubprocessError, OSError):
            if attempt == 3:
                raise
            time.sleep(attempt * 2)
    git(repo, "rev-parse", "--verify", f"{remote_ref}^{{commit}}")
    return remote_ref


def clone_for_measurement(
    root: Path,
    owner: str,
    name: str,
    metadata: dict[str, Any],
) -> Path:
    """Make a temporary bare clone when a recent public repo is not local."""
    if not is_safe_github_component(owner) or not is_safe_github_component(name):
        raise RuntimeError(f"unsafe GitHub owner or repository name: {name}")
    branch = metadata_default_branch(metadata)
    destination = root / name
    try:
        result = subprocess.run(
            [
                "git",
                "clone",
                "--bare",
                "--quiet",
                "--single-branch",
                "--branch",
                branch,
                f"https://github.com/{owner}/{name}.git",
                str(destination),
            ],
            check=False,
            capture_output=True,
            text=True,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0", "LC_ALL": "C"},
            timeout=600,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(f"could not clone {name}") from exc
    if result.returncode != 0:
        raise RuntimeError(f"could not clone {name}")
    return destination


def activity_score(commit_count: int, changed_lines: int) -> float:
    """Favor sustained work while log-scaling churn from generated files."""
    return commit_count * math.log2(2 + changed_lines)


def summarize(
    repo: Path,
    ref: str,
    since: datetime,
    until: datetime,
) -> dict[str, int | float | str] | None:
    tip = git(
        repo,
        "rev-list",
        "--first-parent",
        "-1",
        f"--before={until.isoformat()}",
        ref,
        "--",
    ).strip()
    if not tip:
        return None

    commit_count_text = git(
        repo,
        "rev-list",
        "--count",
        # Unlike --since, this visits the full reachable graph before
        # filtering, so one old, clock-skewed commit cannot hide newer-dated
        # ancestors behind it.
        f"--since-as-filter={since.isoformat()}",
        f"--until={until.isoformat()}",
        tip,
        "--",
    ).strip()
    try:
        commit_count = int(commit_count_text)
    except ValueError as exc:
        raise RuntimeError("Git returned an invalid commit count") from exc
    if commit_count <= 0:
        return None

    base = git(
        repo,
        "rev-list",
        "--first-parent",
        "-1",
        f"--before={since.isoformat()}",
        tip,
        "--",
    ).strip()
    if not base:
        base = git(repo, "hash-object", "-t", "tree", "/dev/null").strip()

    additions = 0
    deletions = 0
    diff_output = git(repo, "diff", "--numstat", "--no-renames", base, tip, "--")
    for line in diff_output.splitlines():
        fields = line.split("\t", 2)
        if len(fields) == 3 and fields[0].isdigit() and fields[1].isdigit():
            additions += int(fields[0])
            deletions += int(fields[1])

    changed_lines = additions + deletions
    return {
        "windowDays": (until - since).days,
        "windowStart": since.isoformat(timespec="seconds"),
        "windowEnd": until.isoformat(timespec="seconds"),
        "commitCount": commit_count,
        "additions": additions,
        "deletions": deletions,
        "changedLines": changed_lines,
        "score": round(activity_score(commit_count, changed_lines), 6),
    }


def measure_repository(
    repo: Path,
    metadata: dict[str, Any],
    since: datetime,
    until: datetime,
) -> dict[str, int | float | str] | None:
    branch = metadata_default_branch(metadata)
    ref = fetch_default_branch(repo, branch)
    return summarize(repo, ref, since, until)


def measure_all(
    candidates: dict[str, dict[str, Any]],
    clones: dict[str, Path],
    since: datetime,
    until: datetime,
) -> dict[str, dict[str, int | float | str]]:
    activities: dict[str, dict[str, int | float | str]] = {}
    failures: list[str] = []
    worker_count = min(MAX_WORKERS, max(1, len(candidates)))
    with ThreadPoolExecutor(max_workers=worker_count) as pool:
        futures = {
            pool.submit(
                measure_repository,
                clones[name],
                metadata,
                since,
                until,
            ): name
            for name, metadata in candidates.items()
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                activity = future.result()
            except (RuntimeError, subprocess.SubprocessError, OSError):
                failures.append(name)
                continue
            if activity is not None:
                activities[name] = activity
    if failures:
        names = ", ".join(sorted(failures, key=str.lower))
        raise RuntimeError(f"could not fetch or measure: {names}")
    return activities


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--owner", default=OWNER)
    parser.add_argument(
        "--projects-root",
        type=Path,
        default=Path(os.environ.get("PROJECTS_ROOT", "~/projects")).expanduser(),
    )
    parser.add_argument("--days", type=int, default=DEFAULT_WINDOW_DAYS)
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not is_safe_github_component(args.owner):
        raise SystemExit("--owner must be a valid GitHub account name")
    if args.days < 1:
        raise SystemExit("--days must be at least 1")
    if args.limit < 1:
        raise SystemExit("--limit must be at least 1")
    try:
        repos = json.JSONDecoder().decode(sys.stdin.read())
    except (json.JSONDecodeError, OSError) as exc:
        raise SystemExit(f"repository metadata is not valid JSON: {exc}") from exc

    window_end = datetime.now(timezone.utc).replace(microsecond=0)
    window_start = window_end - timedelta(days=args.days)
    try:
        candidates = recent_candidates(repos, window_start)
        clones = discover_clones(args.projects_root, args.owner, set(candidates))
        missing = set(candidates) - set(clones)
        if len(missing) > MAX_TEMPORARY_CLONES:
            raise RuntimeError(
                f"{len(missing)} recent repositories are missing locally; "
                f"refusing more than {MAX_TEMPORARY_CLONES} temporary clones"
            )
        with tempfile.TemporaryDirectory(prefix="profile-activity-") as temporary:
            temporary_root = Path(temporary)
            for name in sorted(missing, key=str.lower):
                print(f"Temporarily cloning recent repository {name}.", file=sys.stderr)
                clones[name] = clone_for_measurement(
                    temporary_root, args.owner, name, candidates[name]
                )
            activities = measure_all(candidates, clones, window_start, window_end)
    except (RuntimeError, TypeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    enriched = []
    for name, activity in activities.items():
        item = dict(candidates[name])
        item["recentActivity"] = activity
        enriched.append(item)
    enriched.sort(
        key=lambda repo: (
            repo["recentActivity"]["score"],
            repo["recentActivity"]["commitCount"],
            repo["recentActivity"]["changedLines"],
            repo["name"],
        ),
        reverse=True,
    )
    print(
        f"Measured {len(enriched)} active public default branches over "
        f"{args.days} days; emitting the top {min(args.limit, len(enriched))}.",
        file=sys.stderr,
    )
    json.dump(enriched[: args.limit], sys.stdout, separators=(",", ":"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
