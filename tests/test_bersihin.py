import tempfile
import unittest
from pathlib import Path
from unittest import mock

import bersihin


class BersihinTests(unittest.TestCase):
    def test_version(self):
        self.assertRegex(bersihin.__version__, r"^\d+\.\d+\.\d+$")

    def test_home_is_protected(self):
        env = bersihin.detect_environment()
        self.assertTrue(bersihin._is_dangerous_target(env.home, env))

    def test_root_is_protected_on_posix(self):
        env = bersihin.detect_environment()
        if Path("/").exists():
            self.assertTrue(bersihin._is_dangerous_target(Path("/"), env))

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
        self.assertFalse(any(r.root == Path("/") and r.label == "Python __pycache__" for r in rules))

    def test_json_parser_options(self):
        args = bersihin.build_parser().parse_args(["--dry-run", "--json", "--older-than", "3"])
        self.assertTrue(args.dry_run)
        self.assertTrue(args.json)
        self.assertEqual(args.older_than, 3)


if __name__ == "__main__":
    unittest.main()
