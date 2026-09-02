#!/usr/bin/env python3
"""Enrich public-repository metadata with trailing local Git activity.

The profile's "What I'm Building Now" section should reflect substantive work,
not whichever repository most recently received a maintenance push.  This
script joins GitHub repository metadata to clones below ``~/projects`` and
measures unique default-branch commits plus added/deleted lines over a trailing
window.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys


OWNER = "Dicklesworthstone"
COMMIT_PREFIX = "__PROFILE_COMMIT__\t"
EXCLUDED = {"Dicklesworthstone", "homebrew-tap", "scoop-bucket"}


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "LC_ALL": "C"},
        timeout=120,
    )
    return result.stdout


def remote_repo_name(repo: Path) -> str | None:
    """Return the GitHub repository name without ever printing remote URLs."""
    try:
        remote = git(repo, "config", "--get", "remote.origin.url").strip()
    except (subprocess.SubprocessError, OSError):
        return None
    match = re.search(
        rf"github\.com[/:]{re.escape(OWNER)}/([^/?#]+?)(?:\.git)?/?$",
        remote,
        flags=re.IGNORECASE,
    )
    return match.group(1) if match else None


def discover_clones(root: Path, wanted: set[str]) -> dict[str, Path]:
    clones: dict[str, Path] = {}
    try:
        children = list(root.iterdir())
    except OSError as exc:
        print(f"warning: could not scan projects root {root}: {exc}", file=sys.stderr)
        return clones

    wanted_lower = {name.lower(): name for name in wanted}
    for child in children:
        if not child.is_dir() or not (child / ".git").exists():
            continue
        name = remote_repo_name(child)
        canonical = wanted_lower.get((name or child.name).lower())
        if canonical and (
            canonical not in clones or child.name.lower() == canonical.lower()
        ):
            clones[canonical] = child
    return clones


def default_branch_ref(repo: Path) -> str:
    for ref in ("main", "master"):
        try:
            git(repo, "rev-parse", "--verify", f"{ref}^{{commit}}")
        except (subprocess.SubprocessError, OSError):
            continue
        return ref
    try:
        remote_head = git(repo, "symbolic-ref", "refs/remotes/origin/HEAD").strip()
        if remote_head:
            return remote_head
    except (subprocess.SubprocessError, OSError):
        pass
    return "HEAD"


def measure(repo: Path, cutoff: datetime, window_days: int) -> dict[str, int | float]:
    ref = default_branch_ref(repo)
    output = git(
        repo,
        "log",
        ref,
        f"--since={cutoff.isoformat()}",
        "--no-renames",
        f"--format={COMMIT_PREFIX}%H%x09%cI",
        "--shortstat",
    )
    commits: set[str] = set()
    active_days: set[str] = set()
    additions = 0
    deletions = 0
    for line in output.splitlines():
        if line.startswith(COMMIT_PREFIX):
            fields = line.split("\t")
            if len(fields) >= 3:
                commits.add(fields[1])
                active_days.add(fields[2][:10])
            continue
        insertion_match = re.search(r"(\d+) insertion", line)
        deletion_match = re.search(r"(\d+) deletion", line)
        if insertion_match:
            additions += int(insertion_match.group(1))
        if deletion_match:
            deletions += int(deletion_match.group(1))

    commit_count = len(commits)
    churn = additions + deletions
    # Count is the primary activity signal; log-scaled churn rewards substantive
    # changes without allowing one generated-file import to swamp two weeks of
    # sustained work. Active days break near-ties in favor of ongoing projects.
    score = (
        commit_count
        * math.log2(2 + churn)
        * (1 + 0.25 * len(active_days) / window_days)
    )
    return {
        "windowDays": window_days,
        "commitCount": commit_count,
        "additions": additions,
        "deletions": deletions,
        "changedLines": churn,
        "activeDays": len(active_days),
        "score": round(score, 6),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--projects-root",
        type=Path,
        default=Path(os.environ.get("PROJECTS_ROOT", "~/projects")).expanduser(),
    )
    parser.add_argument("--days", type=int, default=14)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.days < 1:
        raise SystemExit("--days must be at least 1")
    try:
        repos = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"repository metadata is not valid JSON: {exc}") from exc
    if not isinstance(repos, list):
        raise SystemExit("repository metadata must be a JSON array")

    cutoff = datetime.now(timezone.utc) - timedelta(days=args.days)
    candidates = {
        str(repo.get("name"))
        for repo in repos
        if isinstance(repo, dict)
        and repo.get("name")
        and not repo.get("isArchived")
        and not repo.get("isFork")
        and repo.get("name") not in EXCLUDED
        and "12_west" not in str(repo.get("name")).lower()
        and "12-west" not in str(repo.get("name")).lower()
        and "12west" not in str(repo.get("name")).lower()
        and str(repo.get("pushedAt") or "") >= cutoff.isoformat()
    }
    clones = discover_clones(args.projects_root, candidates)
    repos_by_name = {
        str(repo["name"]): repo
        for repo in repos
        if isinstance(repo, dict) and repo.get("name") in clones
    }
    enriched = []
    worker_count = min(8, max(1, len(repos_by_name)))
    with ThreadPoolExecutor(max_workers=worker_count) as pool:
        futures = {
            pool.submit(measure, clones[name], cutoff, args.days): name
            for name in repos_by_name
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                activity = future.result()
            except (subprocess.SubprocessError, OSError) as exc:
                print(f"warning: could not measure {name}: {exc}", file=sys.stderr)
                continue
            print(
                f"Measured {name}: {activity['commitCount']} commits, "
                f"{activity['changedLines']} changed lines",
                file=sys.stderr,
            )
            if activity["commitCount"] <= 0:
                continue
            item = dict(repos_by_name[name])
            item["recentActivity"] = activity
            enriched.append(item)

    enriched.sort(
        key=lambda repo: (
            repo["recentActivity"]["score"],
            repo["recentActivity"]["commitCount"],
            repo["recentActivity"]["changedLines"],
        ),
        reverse=True,
    )
    print(
        f"Measured {len(enriched)} active public clones over {args.days} days "
        f"({len(clones)}/{len(candidates)} recent repositories found locally).",
        file=sys.stderr,
    )
    json.dump(enriched, sys.stdout, separators=(",", ":"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
