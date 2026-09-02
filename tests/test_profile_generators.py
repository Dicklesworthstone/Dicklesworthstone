from __future__ import annotations

import json
import os
import stat
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from scripts import recent_activity, star_history, update_readme

UTC = timezone.utc


def repo_payload(name: str = "example", **activity_overrides: object) -> dict:
    activity = {
        "windowDays": 14,
        "windowStart": "2026-08-19T00:00:00+00:00",
        "windowEnd": "2026-09-02T00:00:00+00:00",
        "commitCount": 3,
        "additions": 20,
        "deletions": 5,
        "changedLines": 25,
        "score": 14.264663,
    }
    activity.update(activity_overrides)
    return {
        "name": name,
        "url": f"https://github.com/Dicklesworthstone/{name}",
        "description": "An example",
        "isArchived": False,
        "isFork": False,
        "primaryLanguage": {"name": "Python", "color": "#3572A5"},
        "recentActivity": activity,
    }


class RecentActivityTests(unittest.TestCase):
    def test_candidates_use_parsed_times_and_fail_closed_flags(self) -> None:
        since = datetime(2026, 8, 20, tzinfo=UTC)
        valid = {
            "name": "valid",
            "pushedAt": "2026-08-20T01:00:00-04:00",
            "isArchived": False,
            "isFork": False,
        }
        repos = [
            valid,
            {**valid, "name": "stale", "pushedAt": "2026-08-19T23:00:00Z"},
            {**valid, "name": "12-West"},
        ]
        self.assertEqual(
            recent_activity.recent_candidates(repos, since), {"valid": valid}
        )
        with self.assertRaises(TypeError):
            recent_activity.recent_candidates(
                [{**valid, "name": "missing-flag", "isFork": None}], since
            )
        with self.assertRaises(TypeError):
            recent_activity.recent_candidates(
                [{**valid, "name": "bad-time", "pushedAt": "yesterday"}], since
            )

    def test_summarize_counts_commits_and_window_diff(self) -> None:
        diff_output = "10\t2\tfirst.txt\n-\t-\tbinary.dat\n3\t4\tsecond.txt"
        since = datetime(2026, 8, 19, tzinfo=UTC)
        until = datetime(2026, 9, 2, tzinfo=UTC)
        with patch.object(
            recent_activity,
            "git",
            side_effect=["tip\n", "3\n", "base\n", diff_output],
        ) as git_mock:
            summary = recent_activity.summarize(
                Path("/repo"), "origin/main", since, until
            )
        if summary is None:
            self.fail("expected recent activity")
        self.assertEqual(summary["commitCount"], 3)
        self.assertEqual(summary["additions"], 13)
        self.assertEqual(summary["deletions"], 6)
        self.assertEqual(summary["changedLines"], 19)
        self.assertEqual(summary["windowDays"], 14)
        self.assertIn("--first-parent", git_mock.call_args_list[0].args)
        self.assertIn("--first-parent", git_mock.call_args_list[2].args)

    def test_fetch_default_branch_forces_only_the_named_remote_ref(self) -> None:
        calls: list[tuple[str, ...]] = []

        def fake_git(_repo: Path, *args: str) -> str:
            calls.append(args)
            return ""

        with patch.object(recent_activity, "git", side_effect=fake_git):
            ref = recent_activity.fetch_default_branch(Path("/repo"), "main")
        self.assertEqual(ref, "refs/remotes/origin/main")
        self.assertEqual(calls[0], ("check-ref-format", "--branch", "main"))
        self.assertIn(
            "+refs/heads/main:refs/remotes/origin/main",
            calls[1],
        )
        self.assertEqual(calls[2][-1], "refs/remotes/origin/main^{commit}")

    def test_discovery_requires_a_matching_owner_remote(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in ("right", "wrong"):
                (root / name / ".git").mkdir(parents=True)

            def fake_remote(path: Path, _owner: str) -> str | None:
                return "right" if path.name == "right" else "someone-elses-repo"

            with patch.object(
                recent_activity, "remote_repo_name", side_effect=fake_remote
            ):
                found = recent_activity.discover_clones(
                    root, "Dicklesworthstone", {"right", "wrong"}
                )
        self.assertEqual(set(found), {"right"})


class ReadmeActivityTests(unittest.TestCase):
    def load(self, repos: list[dict]) -> list[dict]:
        with patch.dict(
            os.environ,
            {"RECENT_ACTIVITY_JSON_CONTENT": json.dumps(repos)},
            clear=False,
        ):
            return update_readme.load_recent_repos()

    def test_activity_payload_requires_consistent_integer_line_totals(self) -> None:
        valid = repo_payload("valid")
        fractional = repo_payload("fractional", commitCount=1.5)
        inconsistent = repo_payload("inconsistent", changedLines=26)
        wrong_url = repo_payload("wrong-url")
        wrong_url["url"] += "/issues"
        self.assertEqual(self.load([fractional, inconsistent, wrong_url, valid]), [])
        self.assertEqual([repo["name"] for repo in self.load([valid])], ["valid"])

    def test_table_uses_the_measured_window_and_explicit_add_delete_counts(
        self,
    ) -> None:
        with patch.dict(
            os.environ,
            {
                "RECENT_ACTIVITY_JSON_CONTENT": json.dumps(
                    [
                        repo_payload(
                            "example",
                            windowDays=7,
                            windowStart="2026-08-26T00:00:00+00:00",
                        )
                    ]
                )
            },
            clear=False,
        ):
            table = update_readme.build_recent_repos_table()
        self.assertIn("trailing 7 days", table)
        self.assertIn("| Project | Lang | 7-day activity |", table)
        self.assertIn("3 commits<br>+20 / −5 lines", table)


class StarHistoryTests(unittest.TestCase):
    def test_stargazer_pages_are_deduplicated_by_login(self) -> None:
        raw = (
            "alice\t2026-01-01T00:00:00Z\n"
            "bob\t2026-01-02T00:00:00Z\n"
            "alice\t2026-01-01T00:00:00Z\n"
        )
        with patch.object(star_history, "gh", return_value=raw):
            stamps = star_history.starred_at("example")
        self.assertEqual(len(stamps), 2)
        self.assertLess(stamps[0], stamps[1])

    def test_render_uses_only_selected_series_for_the_time_axis(self) -> None:
        selected = "selected&safe"
        series = {
            selected: [datetime(2025, 1, 15, tzinfo=UTC)],
            "unselected": [datetime(2020, 1, 1, tzinfo=UTC)],
        }
        svg = star_history.render(
            star_history.DARK,
            series,
            [selected],
            {selected: 1, "unselected": 1},
            {selected: 0, "unselected": 0},
        )
        self.assertIn("Jan 2025", svg)
        self.assertNotIn("Jan 2020", svg)
        self.assertIn("selected&amp;safe", svg)

    def test_atomic_write_replaces_content_with_normal_permissions(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "chart.svg"
            target.write_text("old", encoding="utf-8")
            star_history.write_atomically(target, "new\n")
            self.assertEqual(target.read_text(encoding="utf-8"), "new\n")
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o644)


if __name__ == "__main__":
    unittest.main()
