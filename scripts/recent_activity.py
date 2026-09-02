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
    children_by_name = {child.name.lower(): child for child in children}
    for lowered, canonical in wanted_lower.items():
        child = children_by_name.get(lowered)
        if child and child.is_dir() and (child / ".git").exists():
            clones[canonical] = child

    if len(clones) == len(wanted):
        return clones

    for child in children:
        if not child.is_dir() or not (child / ".git").exists():
            continue
        name = remote_repo_name(child)
        canonical = wanted_lower.get((name or child.name).lower())
        if canonical and canonical not in clones:
            clones[canonical] = child
    return clones


def default_branch_ref(repo: Path, preferred: str | None = None) -> str:
    candidates = []
    if preferred:
        candidates.extend(
            (f"refs/heads/{preferred}", f"refs/remotes/origin/{preferred}")
        )
    candidates.extend(("refs/heads/main", "refs/heads/master"))
    for qualified in dict.fromkeys(candidates):
        try:
            git(repo, "rev-parse", "--verify", f"{qualified}^{{commit}}")
        except (subprocess.SubprocessError, OSError):
            continue
        return qualified
    try:
        remote_head = git(repo, "symbolic-ref", "refs/remotes/origin/HEAD").strip()
        if remote_head:
            return remote_head
    except (subprocess.SubprocessError, OSError):
        pass
    return "HEAD"


def metadata_default_branch(repo: dict) -> str | None:
    branch = repo.get("defaultBranchRef")
    if not isinstance(branch, dict):
        return None
    name = branch.get("name")
    return name if isinstance(name, str) and name else None


def parse_shortstat(output: str) -> tuple[int, int]:
    additions = 0
    deletions = 0
    for line in output.splitlines():
        insertion_match = re.search(r"(\d+) insertion", line)
        deletion_match = re.search(r"(\d+) deletion", line)
        if insertion_match:
            additions += int(insertion_match.group(1))
        if deletion_match:
            deletions += int(deletion_match.group(1))
    return additions, deletions


def activity_score(
    commit_count: int, changed_lines: int, active_days: int, window_days: int
) -> float:
    return (
        commit_count
        * math.log2(2 + changed_lines)
        * (1 + 0.25 * min(active_days, window_days) / window_days)
    )


def summarize(
    repo: Path, cutoff: datetime, window_days: int, preferred_branch: str | None
) -> dict[str, object]:
    ref = default_branch_ref(repo, preferred_branch)
    output = git(
        repo,
        "log",
        ref,
        f"--since={cutoff.isoformat()}",
        f"--format={COMMIT_PREFIX}%H%x09%cI",
        "--",
    )
    commits: set[str] = set()
    active_days: set[str] = set()
    for line in output.splitlines():
        if line.startswith(COMMIT_PREFIX):
            fields = line.split("\t")
            if len(fields) >= 3:
                commits.add(fields[1])
                active_days.add(fields[2][:10])

    base = git(
        repo,
        "rev-list",
        "-1",
        f"--before={cutoff.isoformat()}",
        ref,
        "--",
    ).strip()
    if not base:
        base = git(repo, "hash-object", "-t", "tree", "/dev/null").strip()
    net_additions, net_deletions = parse_shortstat(
        git(repo, "diff", "--shortstat", "--no-renames", base, ref, "--")
    )
    net_churn = net_additions + net_deletions
    return {
        "windowDays": window_days,
        "commitCount": len(commits),
        "additions": net_additions,
        "deletions": net_deletions,
        "changedLines": net_churn,
        "activeDays": len(active_days),
        "score": round(
            activity_score(len(commits), net_churn, len(active_days), window_days),
            6,
        ),
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
            pool.submit(
                summarize,
                clones[name],
                cutoff,
                args.days,
                metadata_default_branch(repos_by_name[name]),
            ): name
            for name in repos_by_name
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                activity = future.result()
            except (subprocess.SubprocessError, OSError) as exc:
                print(f"warning: could not summarize {name}: {exc}", file=sys.stderr)
                continue
            if int(activity["commitCount"]) <= 0:
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
