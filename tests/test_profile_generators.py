from __future__ import annotations

import http.client
import json
import os
import re
import stat
import subprocess
import tempfile
import unittest
import urllib.request
from datetime import datetime, timedelta, timezone
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

    def test_candidates_skip_a_new_empty_repository(self) -> None:
        # GitHub gives an empty repo a fresh pushedAt and no default branch.
        since = datetime(2026, 8, 20, tzinfo=UTC)
        valid = {
            "name": "valid",
            "pushedAt": "2026-08-21T00:00:00Z",
            "isArchived": False,
            "isEmpty": False,
            "isFork": False,
            "defaultBranchRef": {"name": "main"},
        }
        empty = {
            **valid,
            "name": "brand-new",
            "isEmpty": True,
            "defaultBranchRef": {"name": ""},
        }
        self.assertEqual(
            recent_activity.recent_candidates([valid, empty], since),
            {"valid": valid},
        )
        with self.assertRaises(TypeError):
            recent_activity.recent_candidates(
                [{**valid, "isEmpty": "false"}], since
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

    def test_fetch_default_branch_retries_a_transient_fetch_failure(self) -> None:
        calls: list[tuple[str, ...]] = []
        fetch_attempts = 0

        def fake_git(_repo: Path, *args: str) -> str:
            nonlocal fetch_attempts
            calls.append(args)
            if args == ("rev-parse", "--is-shallow-repository"):
                return "false\n"
            if args and args[0] == "fetch":
                fetch_attempts += 1
                if fetch_attempts == 1:
                    raise subprocess.CalledProcessError(1, args)
            return ""

        with (
            patch.object(recent_activity, "git", side_effect=fake_git),
            patch.object(recent_activity.time, "sleep") as sleep_mock,
        ):
            recent_activity.fetch_default_branch(Path("/repo"), "main")
        self.assertEqual(fetch_attempts, 2)
        self.assertEqual(
            calls.count(("rev-parse", "--is-shallow-repository")), 2
        )
        sleep_mock.assert_called_once_with(2)

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

    def test_discovery_prefers_the_canonical_directory_among_duplicate_clones(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            canonical = root / "example"
            alternate = root / "release-example"
            for clone in (alternate, canonical):
                (clone / ".git").mkdir(parents=True)
            with patch.object(
                recent_activity,
                "remote_repo_name",
                return_value="example",
            ):
                found = recent_activity.discover_clones(
                    root, "Dicklesworthstone", {"example"}
                )
        self.assertEqual(found, {"example": canonical})


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

    def test_activity_table_prefers_curated_profile_description(self) -> None:
        repo = repo_payload("frankengit")
        repo["description"] = "Unedited GitHub description"
        with patch.dict(
            os.environ,
            {"RECENT_ACTIVITY_JSON_CONTENT": json.dumps([repo])},
            clear=False,
        ):
            table = update_readme.build_recent_repos_table()
        self.assertIn(
            "Git-compatible forge for human and coding-agent workflows", table
        )
        self.assertNotIn("Unedited GitHub description", table)

    def test_activity_table_falls_back_to_the_curated_readme_name(self) -> None:
        readme = (
            "| **[LLM-Aided OCR](https://github.com/Dicklesworthstone/llm_aided_ocr)** |\n"
            "| [**Agent Farm**](https://github.com/Dicklesworthstone/claude_code_agent_farm) |\n"
            "| **[Visual A* Pathfinding](https://github.com/Dicklesworthstone/visual_astar_python)** |\n"
            "| **[Pipe A\\|B](https://github.com/Dicklesworthstone/pipe_repo)** |\n"
            "<!-- BEGIN AUTO-BUILDING-NOW -->\n"
            "| [**Stale Name**](https://github.com/Dicklesworthstone/unlisted_repo) |\n"
            "<!-- END AUTO-BUILDING-NOW -->\n"
        )
        curated = update_readme.curated_display_names(readme)
        self.assertEqual(curated["llm_aided_ocr"], "LLM-Aided OCR")
        self.assertEqual(curated["claude_code_agent_farm"], "Agent Farm")
        self.assertEqual(curated["pipe_repo"], "Pipe A|B")
        self.assertNotIn("unlisted_repo", curated)
        repos = [
            repo_payload("llm_aided_ocr"),
            repo_payload("visual_astar_python"),
            repo_payload("pipe_repo"),
            repo_payload("unlisted_repo"),
            repo_payload("frankengit"),
        ]
        with patch.dict(
            os.environ,
            {"RECENT_ACTIVITY_JSON_CONTENT": json.dumps(repos)},
            clear=False,
        ):
            table = update_readme.build_recent_repos_table(curated)
        self.assertIn("[**LLM-Aided OCR**]", table)
        self.assertIn("[**Visual A\\* Pathfinding**]", table)
        self.assertIn("[**Pipe A\\|B**]", table)
        self.assertIn("[**Unlisted Repo**]", table)
        self.assertIn("[**FrankenGit**]", table)

    def test_recent_activity_exclusions_match_the_readme_generator(self) -> None:
        # A repo excluded on one side only makes update_readme drop the whole
        # measurement and keep the stale section.
        self.assertEqual(recent_activity.EXCLUDED, update_readme.RECENT_EXCLUDE)

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

    def test_malformed_writing_item_preserves_existing_section(self) -> None:
        items = [
            {
                "title": "Valid",
                "href": "https://www.jeffreyemanuel.com/writing/valid",
                "blurb": "Complete metadata.",
            },
            {
                "href": "https://www.jeffreyemanuel.com/writing/missing-title",
                "blurb": "Incomplete metadata.",
            },
        ]
        with patch.object(update_readme, "fetch_writing_items", return_value=items):
            self.assertEqual(update_readme.build_writing_block(), "")

    def test_writing_block_prefers_curated_blurb_and_plain_separator(self) -> None:
        items = [
            {
                "title": "The Overprompting Trap",
                "href": "https://www.jeffreyemanuel.com/writing/overprompting/",
                "blurb": "Unedited site blurb",
            }
        ]
        with patch.object(update_readme, "fetch_writing_items", return_value=items):
            block = update_readme.build_writing_block()
        self.assertIn("**: How excessive constraints hurt model output", block)
        self.assertNotIn("Unedited site blurb", block)
        self.assertNotIn("—", block)

    def test_writing_block_omits_separator_when_blurb_is_empty(self) -> None:
        items = [
            {
                "title": "Article Without a Blurb",
                "href": "https://www.jeffreyemanuel.com/writing/no-blurb",
                "blurb": None,
            }
        ]
        with patch.object(update_readme, "fetch_writing_items", return_value=items):
            block = update_readme.build_writing_block()
        self.assertEqual(
            block,
            "- **[Article Without a Blurb]"
            "(https://www.jeffreyemanuel.com/writing/no-blurb)**",
        )

    def test_main_is_idempotent_with_a_million_scale_follower_label(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "README.md"
            target.write_text(update_readme.README.read_text(encoding="utf-8"))
            with (
                patch.object(update_readme, "README", target),
                patch.object(update_readme, "load_repo_star_counts", return_value={}),
                patch.object(update_readme, "build_recent_repos_table", return_value=""),
                patch.object(update_readme, "build_writing_block", return_value=""),
                patch.dict(
                    os.environ,
                    {"X_FOLLOWERS_LABEL": "1.2M"},
                    clear=False,
                ),
            ):
                update_readme.main()
                first_pass = target.read_text(encoding="utf-8")
                update_readme.main()
            self.assertEqual(target.read_text(encoding="utf-8"), first_pass)
            self.assertIn("![X: 1.2M]", first_pass)
            self.assertIn("1.2M X followers", first_pass)


class StarHistoryTests(unittest.TestCase):
    def test_github_api_call_retries_a_transient_failure(self) -> None:
        failed = subprocess.CompletedProcess([], 1, "", "HTTP 502")
        succeeded = subprocess.CompletedProcess([], 0, "payload", "")
        with (
            patch.object(
                star_history.subprocess,
                "run",
                side_effect=[failed, succeeded],
            ) as run_mock,
            patch.object(star_history.time, "sleep") as sleep_mock,
        ):
            self.assertEqual(star_history.gh(["api", "endpoint"]), "payload")
        self.assertEqual(run_mock.call_count, 2)
        sleep_mock.assert_called_once_with(2)

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

    def test_adaptive_selection_keeps_fetching_while_a_new_growth_leader_is_possible(
        self,
    ) -> None:
        # "growing" is 14th and "steady" 15th while 100 is the top growth. A
        # remaining 150-star repo cannot be charted itself, but if all 150
        # stars are recent it becomes the growth leader and swaps those two.
        series = {
            f"core-{index}": [datetime(2026, 9, 1, tzinfo=UTC)]
            for index in range(star_history.MAX_SERIES - 1)
        }
        series["growing"] = [datetime(2026, 9, 1, tzinfo=UTC)]
        series["steady"] = [datetime(2026, 9, 1, tzinfo=UTC)]
        totals = {repo: 1_000 for repo in series}
        growth = {repo: 100 for repo in series}
        totals["growing"], growth["growing"] = 500, 90
        growth["steady"] = 30
        self.assertIn("growing", star_history.select(series, totals, growth))
        spiked = {
            **series,
            "spike": [datetime(2026, 9, 1, tzinfo=UTC)],
        }
        chosen = star_history.select(
            spiked, {**totals, "spike": 150}, {**growth, "spike": 150}
        )
        self.assertNotIn("spike", chosen)
        self.assertIn("steady", chosen)
        self.assertNotIn("growing", chosen)
        self.assertFalse(
            star_history.remaining_cannot_qualify(
                [("spike", 150)], series, totals, growth
            )
        )

    def test_year_label_near_the_axis_end_keeps_only_its_gridline(self) -> None:
        def axis_labels(snapshot: datetime) -> list[str]:
            svg = star_history.render(
                star_history.DARK,
                {"repo": [datetime(2023, 7, 10, tzinfo=UTC)]},
                ["repo"],
                {"repo": 1},
                {"repo": 0},
                snapshot,
            )
            return re.findall(r'y="622"[^>]*>([^<]+)</text>', svg)

        self.assertEqual(
            axis_labels(datetime(2027, 1, 20, tzinfo=UTC)),
            ["Jul 2023", "2024", "2025", "2026", "Jan 2027"],
        )
        self.assertEqual(
            axis_labels(datetime(2027, 6, 1, tzinfo=UTC)),
            ["Jul 2023", "2024", "2025", "2026", "2027", "Jun 2027"],
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

    def test_conflicting_duplicate_stargazer_is_rejected(self) -> None:
        raw = (
            "Alice\t2026-01-01T00:00:00Z\n"
            "alice\t2026-01-02T00:00:00Z\n"
        )
        with (
            patch.object(star_history, "gh", return_value=raw),
            self.assertRaises(RuntimeError),
        ):
            star_history.starred_at("example")

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

    def test_render_uses_profile_display_name_for_asupersync(self) -> None:
        repo = "asupersync"
        svg = star_history.render(
            star_history.DARK,
            {repo: [datetime(2026, 9, 1, tzinfo=UTC)]},
            [repo],
            {repo: 1},
            {repo: 0},
            datetime(2026, 9, 2, tzinfo=UTC),
        )
        self.assertIn(">Asupersync</text>", svg)
        self.assertNotIn(">asupersync</text>", svg)

    @staticmethod
    def rising_series(
        snapshot: datetime, before: int, during: int
    ) -> list[datetime]:
        """`before` stars well before the rising window, `during` inside it."""
        old = snapshot - timedelta(days=star_history.RISING_WINDOW_DAYS + 30)
        recent = snapshot - timedelta(days=2)
        return [old] * before + [recent] * during

    def test_rising_picks_need_both_absolute_and_relative_growth(self) -> None:
        snapshot = datetime(2026, 10, 12, tzinfo=UTC)
        series = {
            "launch": self.rising_series(snapshot, 0, 25),  # new: 25 / 20
            "surge": self.rising_series(snapshot, 40, 40),  # +100%
            "boundary": self.rising_series(snapshot, 80, 20),  # exactly +20, 25%
            "tiny": self.rising_series(snapshot, 2, 4),  # the "2 -> 6" case
            "steady": self.rising_series(snapshot, 200, 30),  # +30 but only 15%
            "almost": self.rising_series(snapshot, 81, 20),  # 24.7%
            "charted": self.rising_series(snapshot, 0, 500),  # in the main panel
        }
        picks = star_history.rising_picks(series, {"charted"}, snapshot)
        self.assertEqual([p.repo for p in picks], ["launch", "surge", "boundary"])
        launch = picks[0]
        self.assertEqual((launch.start, launch.gain, launch.total), (0, 25, 25))
        self.assertAlmostEqual(launch.relative, 25 / star_history.RISING_MIN_GAIN)
        ranked = star_history.rising_candidates(series, {"charted"}, snapshot)
        self.assertNotIn("charted", [p.repo for p in ranked])
        self.assertEqual(len(ranked), len(series) - 1)

    def test_rising_picks_are_capped_and_count_the_window_start_inside(self) -> None:
        snapshot = datetime(2026, 10, 12, tzinfo=UTC)
        series = {
            f"riser-{index}": self.rising_series(snapshot, 0, 30 + index)
            for index in range(star_history.MAX_RISING + 2)
        }
        picks = star_history.rising_picks(series, set(), snapshot)
        self.assertEqual(len(picks), star_history.MAX_RISING)
        self.assertEqual(picks[0].repo, f"riser-{star_history.MAX_RISING + 1}")
        cutoff = snapshot - timedelta(days=star_history.RISING_WINDOW_DAYS)
        edge = {"edge": [cutoff - timedelta(seconds=1)] * 10 + [cutoff] * 20}
        (pick,) = star_history.rising_candidates(edge, set(), snapshot)
        self.assertEqual((pick.start, pick.gain), (10, 20))

    def test_main_keeps_fetching_while_a_rising_pick_is_possible(self) -> None:
        now = datetime.now(UTC)
        old = now - timedelta(days=400)
        recent = now - timedelta(days=1)
        big = [old] * 900 + [recent] * 100
        timelines = {f"big-{index}": big for index in range(star_history.MAX_SERIES)}
        timelines.update({f"mid-{index}": [old] * 100 for index in range(6)})
        timelines["riser"] = [recent] * 30
        timelines["quiet"] = [old] * 10
        candidates = [(repo, len(stamps)) for repo, stamps in timelines.items()]
        fetched: list[str] = []
        written: dict[str, str] = {}

        def fake_starred_at(repo: str) -> list[datetime]:
            fetched.append(repo)
            return list(timelines[repo])

        def capture(artifacts: list[tuple[Path, str]]) -> None:
            written.update({path.name: content for path, content in artifacts})

        with (
            patch.object(star_history, "candidate_repos", return_value=candidates),
            patch.object(star_history, "starred_at", side_effect=fake_starred_at),
            patch.object(star_history, "write_svg_pair", side_effect=capture),
        ):
            self.assertEqual(star_history.main(), 0)
        # The 20 initial candidates alone already prove the main selection;
        # the old stopping rule quit there and never saw "riser".
        self.assertIn("riser", fetched)
        self.assertNotIn("quiet", fetched)
        for name in ("star_history.svg", "star_history-light.svg"):
            self.assertIn(">Rising fast</text>", written[name])
            self.assertIn(">riser</text>", written[name])
            self.assertIn(
                f'height="{star_history.HEIGHT + star_history.RISING_HEIGHT}"',
                written[name],
            )

    def test_rising_panel_without_picks_says_so(self) -> None:
        snapshot = datetime(2026, 10, 12, tzinfo=UTC)
        svg = star_history.render(
            star_history.LIGHT,
            {"repo": [datetime(2026, 1, 1, tzinfo=UTC)]},
            ["repo"],
            {"repo": 1},
            {"repo": 0},
            snapshot,
            [],
        )
        self.assertIn("cleared both bars", svg)
        self.assertIn("and 0 smaller repositories rising fastest", svg)
        self.assertIn(">Sep 14</text>", svg)
        self.assertIn(">Oct 12</text>", svg)

    def test_rising_legend_uses_profile_names_and_marks_new_repos(self) -> None:
        snapshot = datetime(2026, 10, 12, tzinfo=UTC)
        series = {
            "repo": [datetime(2026, 1, 1, tzinfo=UTC)],
            "doodlestein_self_releaser": self.rising_series(snapshot, 42, 35),
            "brand_new_thing": self.rising_series(snapshot, 0, 22),
        }
        picks = star_history.rising_picks(series, {"repo"}, snapshot)
        svg = star_history.render(
            star_history.DARK, series, ["repo"], {"repo": 1}, {"repo": 0},
            snapshot, picks,
        )
        self.assertIn(">Doodlestein Self-Releaser</text>", svg)
        self.assertIn("(+83%)", svg)
        self.assertIn(">brand_new_thing</text>", svg)
        self.assertIn("(new)", svg)

    def test_axis_marks_drop_interior_labels_that_touch_the_ends(self) -> None:
        marks = [(100.0, "Sep 14"), (300.0, "Sep 21"), (480.0, "Oct 2"), (500.0, "Oct 3")]
        placed = star_history.axis_marks_without_collisions(marks, 100.0, 500.0)
        self.assertEqual(
            placed,
            [(100.0, "Sep 14", "start"), (300.0, "Sep 21", "middle"), (500.0, "Oct 3", "end")],
        )

    def test_atomic_write_replaces_content_with_normal_permissions(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "chart.svg"
            target.write_text("old", encoding="utf-8")
            star_history.write_atomically(target, "new\n")
            self.assertEqual(target.read_text(encoding="utf-8"), "new\n")
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o644)

    def test_svg_pair_rolls_back_first_theme_if_second_write_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            dark = root / "dark.svg"
            light = root / "light.svg"
            dark.write_text("old dark", encoding="utf-8")
            light.write_text("old light", encoding="utf-8")
            real_write = star_history.write_atomically

            def fail_new_light(path: Path, content: str) -> None:
                if path == light and content == "new light":
                    raise OSError("simulated disk failure")
                real_write(path, content)

            with (
                patch.object(
                    star_history, "write_atomically", side_effect=fail_new_light
                ),
                self.assertRaises(OSError),
            ):
                star_history.write_svg_pair(
                    [(dark, "new dark"), (light, "new light")]
                )
            self.assertEqual(dark.read_text(encoding="utf-8"), "old dark")
            self.assertEqual(light.read_text(encoding="utf-8"), "old light")


if __name__ == "__main__":
    unittest.main()
