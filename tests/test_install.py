"""Exercise installer behavior and skill reference integrity against isolated destinations."""
import pathlib
import re
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        self.config = self.root / "config with spaces"
        self.skill = self.root / "skills with spaces" / "dev-flow"

    def run_install(self, *extra):
        return subprocess.run(
            ["bash", str(ROOT / "install.sh"), "--config-dir", str(self.config),
             "--skill-dir", str(self.skill), *extra],
            capture_output=True, text=True,
        )

    def assert_skill_matches(self, destination=None):
        dest = destination or self.skill
        source = ROOT / "skills/dev-flow"
        expected = {p.relative_to(source): p.read_bytes()
                    for p in source.rglob("*") if p.is_file()}
        actual = {p.relative_to(dest): p.read_bytes()
                  for p in dest.rglob("*") if p.is_file()}
        self.assertEqual(expected, actual)

    def test_fresh_install_and_repeated_install(self):
        for _ in range(2):
            result = self.run_install()
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assert_skill_matches()
        self.assertEqual((self.config / "AGENTS.md").read_bytes(),
                         (ROOT / "config/AGENTS.md").read_bytes())
        self.assertFalse(list(self.config.glob("AGENTS.md.proposed-*")))

    def test_custom_guidance_and_old_skill_are_preserved(self):
        self.config.mkdir()
        original = b"# Private rules\n\nKeep project-specific restrictions.\n"
        (self.config / "AGENTS.md").write_bytes(original)
        self.skill.mkdir(parents=True)
        (self.skill / "old-reference.md").write_text("Old custom reference")
        for _ in range(2):
            result = self.run_install()
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.config / "AGENTS.md").read_bytes(), original)
        proposals = list(self.config.glob("AGENTS.md.proposed-*"))
        self.assertEqual(len(proposals), 2)
        for p in proposals:
            self.assertEqual(p.read_bytes(), (ROOT / "config/AGENTS.md").read_bytes())
        backups = list((self.config / "backups").iterdir())
        self.assertEqual(len(backups), 2)
        self.assertTrue(any((p / "dev-flow/old-reference.md").exists() for p in backups))
        self.assert_skill_matches()

    def test_antigravity_target_install_and_proposal(self):
        agy_config = self.root / "gemini config"
        agy_skill = agy_config / "skills" / "dev-flow"
        result = subprocess.run(
            ["bash", str(ROOT / "install.sh"), "--antigravity",
             "--config-dir", str(agy_config), "--skill-dir", str(agy_skill)],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((agy_config / "GEMINI.md").read_bytes(),
                         (ROOT / "config/AGENTS.md").read_bytes())
        self.assert_skill_matches(agy_skill)

        custom = b"# Custom Antigravity rules\n"
        (agy_config / "GEMINI.md").write_bytes(custom)
        result2 = subprocess.run(
            ["bash", str(ROOT / "install.sh"), "--target", "antigravity",
             "--config-dir", str(agy_config), "--skill-dir", str(agy_skill)],
            capture_output=True, text=True,
        )
        self.assertEqual(result2.returncode, 0, result2.stderr)
        self.assertEqual((agy_config / "GEMINI.md").read_bytes(), custom)
        proposals = list(agy_config.glob("GEMINI.md.proposed-*"))
        self.assertEqual(len(proposals), 1)

    def test_symlink_skill_is_rejected_without_touching_target(self):
        target = self.root / "original"
        target.mkdir()
        marker = target / "keep.txt"
        marker.write_text("unchanged")
        self.skill.parent.mkdir()
        self.skill.symlink_to(target, target_is_directory=True)
        self.assertNotEqual(self.run_install().returncode, 0)
        self.assertEqual(marker.read_text(), "unchanged")
        self.assertTrue(self.skill.is_symlink())

    def test_antigravity_fresh_install_has_one_global_rule(self):
        result = self.run_install("--antigravity")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.config / "GEMINI.md").is_file())
        self.assertFalse((self.config / "rules/AGENTS.md").exists())

    def test_antigravity_duplicate_rule_is_archived(self):
        rule = self.config / "rules/AGENTS.md"
        rule.parent.mkdir(parents=True)
        original = (ROOT / "config/AGENTS.md").read_bytes()
        rule.write_bytes(original)
        (self.config / "GEMINI.md").write_bytes(original)
        result = self.run_install("--antigravity")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(rule.exists())
        archived = list((self.config / "backups").glob("*/antigravity-rules-AGENTS.md"))
        self.assertEqual(len(archived), 1)
        self.assertEqual(archived[0].read_bytes(), original)

    def test_antigravity_custom_rule_is_preserved(self):
        rule = self.config / "rules/AGENTS.md"
        rule.parent.mkdir(parents=True)
        original = b"# Machine-specific Antigravity rule\n"
        rule.write_bytes(original)
        result = self.run_install("--antigravity")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(rule.read_bytes(), original)

    def test_missing_argument_fails_before_writing(self):
        self.assertNotEqual(self.run_install("--skill-dir").returncode, 0)
        self.assertFalse(self.config.exists())

    def test_skill_references_and_links_are_complete(self):
        skill_dir = ROOT / "skills/dev-flow"
        skill_md = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        links = set(re.findall(r"\]\((references/[a-z0-9._-]+\.md)\)", skill_md))
        ref_files = {
            f"references/{p.name}"
            for p in (skill_dir / "references").glob("*.md")
        }
        self.assertEqual(links, ref_files, "Every reference file must be linked from SKILL.md and exist on disk")
        for rel in sorted(ref_files):
            content = (skill_dir / rel).read_text(encoding="utf-8")
            self.assertTrue(content.startswith("# "), f"{rel} must start with an H1 heading")
            self.assertGreater(len(content.splitlines()), 15, f"{rel} should contain substantive guidance")


if __name__ == "__main__":
    unittest.main()
