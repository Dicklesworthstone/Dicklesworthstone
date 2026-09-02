from __future__ import annotations

import http.client
import json
import os
import stat
import tempfile
import unittest
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

from scripts import recent_activity, star_history, update_readme

UTC = timezone.utc


def repo_payload(name: str = "example", **activity_overrides: object) -> dict[str, Any]:
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
        self.assertTrue(
            any(
                str(arg).startswith("--since-as-filter=")
                for arg in git_mock.call_args_list[1].args
            )
        )

    def test_fetch_default_branch_forces_only_the_named_remote_ref(self) -> None:
        calls: list[tuple[str, ...]] = []

        def fake_git(_repo: Path, *args: str) -> str:
            calls.append(args)
            if args == ("rev-parse", "--is-shallow-repository"):
                return "false\n"
            return ""

        with patch.object(recent_activity, "git", side_effect=fake_git):
            ref = recent_activity.fetch_default_branch(Path("/repo"), "main")
        self.assertEqual(ref, "refs/remotes/origin/main")
        self.assertEqual(calls[0], ("check-ref-format", "--branch", "main"))
        self.assertEqual(calls[1], ("rev-parse", "--is-shallow-repository"))
        self.assertIn(
            "+refs/heads/main:refs/remotes/origin/main",
            calls[2],
        )
        self.assertNotIn("--unshallow", calls[2])
        self.assertEqual(calls[3][-1], "refs/remotes/origin/main^{commit}")

    def test_fetch_default_branch_unshallows_before_measurement(self) -> None:
        calls: list[tuple[str, ...]] = []

        def fake_git(_repo: Path, *args: str) -> str:
            calls.append(args)
            if args == ("rev-parse", "--is-shallow-repository"):
                return "true\n"
            return ""

        with patch.object(recent_activity, "git", side_effect=fake_git):
            recent_activity.fetch_default_branch(Path("/repo"), "main")
        self.assertIn("--unshallow", calls[2])

    def test_remote_parser_rejects_lookalike_hosts(self) -> None:
        parse = recent_activity.github_remote_repo_name
        self.assertEqual(
            parse(
                "git@github.com:Dicklesworthstone/example.git",
                "Dicklesworthstone",
            ),
            "example",
        )
        self.assertEqual(
            parse(
                "ssh://git@github.com/Dicklesworthstone/example.git",
                "Dicklesworthstone",
            ),
            "example",
        )
        self.assertIsNone(
            parse(
                "https://evilgithub.com/Dicklesworthstone/example.git",
                "Dicklesworthstone",
            )
        )
        self.assertIsNone(parse("https://[malformed", "Dicklesworthstone"))

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
    def load(self, repos: list[dict[str, Any]]) -> list[dict[str, Any]]:
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

    def test_malformed_language_metadata_fails_closed(self) -> None:
        malformed = repo_payload("malformed")
        malformed["primaryLanguage"] = {"name": "Rust", "color": 123}
        self.assertEqual(self.load([malformed]), [])

    def test_markdown_escape_neutralizes_html(self) -> None:
        self.assertEqual(
            update_readme.markdown_escape("<img src=x>|[label]"),
            "&lt;img src=x&gt;\\|\\[label\\]",
        )
        self.assertEqual(
            update_readme.markdown_escape("one\r\ntwo\tthree"), "one  two three"
        )

    def test_schema_bound_replacements_reject_duplicates(self) -> None:
        with self.assertRaises(SystemExit):
            update_readme.replace_line_any(
                "![Stars](one)\n![Stars](two)\n",
                ["![Stars]("],
                "replacement",
            )
        with self.assertRaises(SystemExit):
            update_readme.replace_pattern_exact("value value", "value", "new")
        self.assertEqual(
            update_readme.replace_pattern_exact(
                "value value", "value", "new", expected=None
            ),
            "new new",
        )

    def test_marker_replacement_requires_one_complete_pair(self) -> None:
        start = "<!-- BEGIN AUTO-TEST -->"
        end = "<!-- END AUTO-TEST -->"
        duplicated = f"{start}\nold\n{end}\n{start}\nold\n{end}\n"
        with self.assertRaises(SystemExit):
            update_readme.between_markers(duplicated, start, end, "new")
        self.assertEqual(
            update_readme.between_markers(f"{start}\nold\n{end}", start, end, "new"),
            f"{start}\nnew\n{end}",
        )

    def test_generated_section_rejects_orphaned_markers(self) -> None:
        start = "<!-- BEGIN AUTO-TEST -->"
        end = "<!-- END AUTO-TEST -->"
        with self.assertRaises(SystemExit):
            update_readme.replace_generated_section(
                f"heading\n{end}\nfooter",
                start,
                end,
                "new",
                "heading\\n",
                "footer",
            )

    def test_legacy_section_migration_rejects_duplicate_boundaries(self) -> None:
        with self.assertRaises(SystemExit):
            update_readme.replace_section_range(
                "heading\nold\nfooter\nheading\nold\nfooter",
                "heading\\n",
                "footer",
                "new",
            )

    def test_readme_atomic_write_preserves_permissions(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "README.md"
            target.write_text("old", encoding="utf-8")
            target.chmod(0o640)
            update_readme.write_atomically(target, "new\n")
            self.assertEqual(target.read_text(encoding="utf-8"), "new\n")
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o640)

    def test_writing_links_are_same_site_and_markdown_safe(self) -> None:
        self.assertEqual(
            update_readme.normalize_writing_href("/writing/a_(careful)_title"),
            "https://www.jeffreyemanuel.com/writing/a_%28careful%29_title",
        )
        self.assertIsNone(
            update_readme.normalize_writing_href("https://example.com/phishing")
        )
        self.assertIsNone(update_readme.normalize_writing_href("https://[malformed"))

    def test_rendered_writing_cards_are_extracted_without_next_metadata(self) -> None:
        page = """
        <a href="/writing/one"><article>
          <h2>One &amp; Only</h2><p>A <em>careful</em> blurb.</p>
        </article></a>
        <a href="https://example.com/writing/trap"><article>
          <h2>Trap</h2><p>Wrong host.</p>
        </article></a>
        """
        self.assertEqual(
            update_readme.extract_rendered_writing_items(page),
            [
                {
                    "title": "One & Only",
                    "href": "https://www.jeffreyemanuel.com/writing/one",
                    "blurb": "A careful blurb.",
                }
            ],
        )

    def test_writing_fetch_is_bounded_and_network_failures_are_nonfatal(self) -> None:
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b"x" * (
            update_readme.MAX_WRITING_BYTES + 1
        )
        with patch.object(urllib.request, "urlopen", return_value=response):
            self.assertEqual(update_readme.fetch_writing_items(), [])

        response.__enter__.return_value.read.side_effect = http.client.IncompleteRead(
            b"partial"
        )
        with patch.object(urllib.request, "urlopen", return_value=response):
            self.assertEqual(update_readme.fetch_writing_items(), [])

    def test_writing_fetch_merges_partial_rendering_with_hydration_data(self) -> None:
        page = b"""
        <a href="/writing/rendered"><article>
          <h2>Rendered</h2><p>Already in the HTML.</p>
        </article></a>
        <script>{"featured":[
          {"title":"Rendered","href":"/writing/rendered","blurb":"Duplicate"},
          {"title":"Hydrated","href":"/writing/hydrated","blurb":"Recovered"}
        ],"archive":[]}</script>
        """
        response = MagicMock()
        response.__enter__.return_value.read.return_value = page
        with patch.object(urllib.request, "urlopen", return_value=response):
            items = update_readme.fetch_writing_items()
        self.assertEqual(
            [item["href"] for item in items],
            [
                "https://www.jeffreyemanuel.com/writing/rendered",
                "https://www.jeffreyemanuel.com/writing/hydrated",
            ],
        )


class StarHistoryTests(unittest.TestCase):
    def test_candidate_pagination_requires_complete_unique_metadata(self) -> None:
        pages = [
            {
                "data": {
                    "user": {
                        "repositories": {
                            "totalCount": 2,
                            "nodes": [{"name": "second", "stargazerCount": 2}],
                            "pageInfo": {"hasNextPage": True, "endCursor": "next"},
                        }
                    }
                }
            },
            {
                "data": {
                    "user": {
                        "repositories": {
                            "totalCount": 2,
                            "nodes": [{"name": "first", "stargazerCount": 5}],
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                        }
                    }
                }
            },
        ]
        with patch.object(star_history, "gh", side_effect=map(json.dumps, pages)):
            self.assertEqual(
                star_history.candidate_repos(), [("first", 5), ("second", 2)]
            )

    def test_adaptive_selection_fetches_until_remaining_growth_cannot_win(self) -> None:
        series = {
            f"repo-{index}": [datetime(2026, 9, 1, tzinfo=UTC)]
            for index in range(star_history.MAX_SERIES)
        }
        totals = {repo: 1_000 - index for index, repo in enumerate(series)}
        growth = {repo: 500 - index for index, repo in enumerate(series)}
        self.assertTrue(
            star_history.remaining_cannot_qualify(
                [("small", 10)], series, totals, growth
            )
        )
        self.assertFalse(
            star_history.remaining_cannot_qualify(
                [("possible-spike", 900)], series, totals, growth
            )
        )

    def test_positive_star_count_requires_timeline_data(self) -> None:
        with (
            patch.object(
                star_history, "candidate_repos", return_value=[("example", 3)]
            ),
            patch.object(star_history, "starred_at", return_value=[]),
            self.assertRaises(RuntimeError),
        ):
            star_history.main()

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

    def test_stargazer_timestamps_must_include_a_timezone(self) -> None:
        with (
            patch.object(
                star_history,
                "gh",
                return_value="alice\t2026-01-01T00:00:00\n",
            ),
            self.assertRaises(RuntimeError),
        ):
            star_history.starred_at("example")

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
            datetime(2026, 9, 2, tzinfo=UTC),
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
