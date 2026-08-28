import tempfile
import unittest
from pathlib import Path
from unittest import mock

import bersihin


class BersihinTests(unittest.TestCase):
    def test_version(self):
        self.assertEqual(bersihin.__version__, "2.0.2")
        self.assertRegex(bersihin.__version__, r"^\d+\.\d+\.\d+$")

    def test_home_is_protected(self):
        env = bersihin.detect_environment()
        self.assertTrue(bersihin._is_dangerous_target(env.home, env))

    def test_root_is_protected_on_posix(self):
        env = bersihin.detect_environment()
        if Path("/").exists():
            self.assertTrue(bersihin._is_dangerous_target(Path("/"), env))

    def test_same_owner_helper(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "owned.tmp"
            p.write_text("x")
            self.assertIsInstance(bersihin._same_owner(p), bool)

    def test_old_age_filter(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "new.tmp"
            p.write_text("x")
            self.assertFalse(bersihin._old_enough(p, 2, p.stat().st_mtime + 10))

    def test_cwd_root_never_becomes_project_rule(self):
        env = bersihin.detect_environment()
        args = bersihin.build_parser().parse_args(["--dry-run"])
        with mock.patch.object(bersihin.Path, "cwd", return_value=Path("/")):
            rules = bersihin.build_rules(env, args)
        self.assertFalse(
            any(
                r.root == Path("/")
                and ("project" in r.label.lower() or "Python __pycache__" in r.label)
                for r in rules
            )
        )

    def test_json_parser_options(self):
        args = bersihin.build_parser().parse_args(
            ["--dry-run", "--json", "--older-than", "3"]
        )
        self.assertTrue(args.dry_run)
        self.assertTrue(args.json)
        self.assertEqual(args.older_than, 3)

    def test_full_parser_option(self):
        args = bersihin.build_parser().parse_args(["--full", "--dry-run"])
        self.assertTrue(args.full)
        self.assertTrue(args.dry_run)

    def test_no_progress_alias(self):
        args = bersihin.build_parser().parse_args(["--no-progress"])
        self.assertTrue(args.quiet)

    def test_force_progress_option(self):
        args = bersihin.build_parser().parse_args(["--force-progress", "--dry-run"])
        self.assertTrue(args.force_progress)

    def test_progress_bar_boundaries(self):
        empty = bersihin._progress_bar(0, 100, width=10)
        half = bersihin._progress_bar(50, 100, width=10)
        full = bersihin._progress_bar(100, 100, width=10)
        self.assertTrue(empty.startswith("[>"))
        self.assertIn(">", half)
        self.assertEqual(full, "[==========]")

    def test_progress_bar_never_overflows(self):
        self.assertEqual(
            bersihin._progress_bar(150, 100, width=8),
            "[========]",
        )

    def test_human_duration(self):
        self.assertEqual(bersihin.human_duration(0.0001), "<1 ms")
        self.assertIn("ms", bersihin.human_duration(0.2))
        self.assertTrue(bersihin.human_duration(2.0).endswith("s"))

    def test_friendly_project_label(self):
        value = bersihin._friendly_label("Python project cache (demo)")
        self.assertIn("demo", value.lower())
        self.assertIn("python", value.lower())

    def test_scan_rule_reports_too_new(self):
        env = bersihin.detect_environment()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / "fresh.log"
            p.write_text("x")
            rule = bersihin.Rule(
                label="test logs",
                category="dev",
                root=root,
                patterns=("*.log",),
                min_age_days=2,
                recursive=False,
            )
            found, row = bersihin.scan_rule(rule, env)
            self.assertEqual(found, [])
            self.assertEqual(row.matched, 1)
            self.assertEqual(row.too_new, 1)
            self.assertEqual(row.eligible, 0)

    def test_scan_rule_finds_eligible_entry(self):
        env = bersihin.detect_environment()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / "cache.tmp"
            p.write_text("cache-data")
            rule = bersihin.Rule(
                label="test cache",
                category="dev",
                root=root,
                patterns=("*.tmp",),
                min_age_days=0,
                recursive=False,
            )
            found, row = bersihin.scan_rule(rule, env)
            self.assertEqual(len(found), 1)
            self.assertEqual(row.status, "FOUND")
            self.assertEqual(row.eligible, 1)
            self.assertGreaterEqual(row.bytes, 1)


if __name__ == "__main__":
    unittest.main()
