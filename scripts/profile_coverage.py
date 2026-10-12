#!/usr/bin/env python3
"""List public repositories the profile neither shows nor deliberately skips.

Reads ``gh repo list --json name,description,isArchived,isEmpty,isFork,...``
output on stdin and prints, as a JSON array, every public, non-fork,
non-archived, non-empty repository that README.md does not link and that
scripts/profile_exclusions.json does not exclude. An exclusion whose
``revisit`` date has arrived is reported again, with its recorded reason, so
an early project gets a second look once it may have matured.

The nightly job hands this list to an unattended Claude Code run, which adds
each repository to the README or records why it stays off. An empty list means
there is nothing to curate.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
EXCLUSIONS = ROOT / "scripts" / "profile_exclusions.json"
OWNER = "Dicklesworthstone"
LINKED_REPO = re.compile(
    rf"github\.com/{OWNER}/([A-Za-z0-9_.-]+)", flags=re.IGNORECASE
)


def linked_repos(readme: str) -> set[str]:
    names = set()
    for match in LINKED_REPO.finditer(readme):
        name = match.group(1)
        if name.lower().endswith(".git"):
            name = name[:-4]
        names.add(name.casefold())
    return names


def load_exclusions(data: object) -> tuple[set[str], dict[str, dict[str, Any]]]:
    if not isinstance(data, dict):
        raise ValueError("exclusions must be a JSON object")
    descriptions = data.get("description_exact", [])
    repos = data.get("repos", {})
    if not isinstance(descriptions, list) or not all(
        isinstance(item, str) for item in descriptions
    ):
        raise ValueError("description_exact must be a list of strings")
    if not isinstance(repos, dict):
        raise ValueError("repos must be an object")
    entries: dict[str, dict[str, Any]] = {}
    for name, entry in repos.items():
        if not isinstance(entry, dict) or not isinstance(entry.get("reason"), str):
            raise ValueError(f"exclusion for {name} needs a reason")
        revisit = entry.get("revisit")
        if revisit is not None:
            date.fromisoformat(revisit)
        entries[name.casefold()] = entry
    return set(descriptions), entries


def uncovered(
    repos: object,
    readme: str,
    exclusions: object,
    today: date,
) -> list[dict[str, Any]]:
    if not isinstance(repos, list):
        raise ValueError("repository metadata must be a JSON array")
    descriptions, excluded = load_exclusions(exclusions)
    linked = linked_repos(readme)
    found: list[dict[str, Any]] = []
    for repo in repos:
        if not isinstance(repo, dict) or not isinstance(repo.get("name"), str):
            raise ValueError("repository metadata entry needs a name")
        name = repo["name"]
        if (
            repo.get("isFork") is not False
            or repo.get("isArchived") is not False
            or repo.get("isEmpty") is True
            or name.casefold() in linked
            or (repo.get("description") or "") in descriptions
        ):
            continue
        entry = excluded.get(name.casefold())
        item = {
            "name": name,
            "description": repo.get("description") or "",
            "stars": repo.get("stargazerCount"),
            "createdAt": repo.get("createdAt"),
            "pushedAt": repo.get("pushedAt"),
        }
        if entry is not None:
            revisit = entry.get("revisit")
            if revisit is None or date.fromisoformat(revisit) > today:
                continue
            item["previousExclusion"] = entry
        found.append(item)
    found.sort(key=lambda item: item["name"].casefold())
    return found


def main() -> int:
    try:
        repos = json.loads(sys.stdin.read())
        readme = README.read_text(encoding="utf-8")
        exclusions = json.loads(EXCLUSIONS.read_text(encoding="utf-8"))
        result = uncovered(repos, readme, exclusions, date.today())
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(
        f"{len(result)} public repositories need a profile decision"
        + (": " + ", ".join(item["name"] for item in result) if result else ""),
        file=sys.stderr,
    )
    json.dump(result, sys.stdout, indent=2)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
