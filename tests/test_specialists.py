"""Offline checks for pinned packaging, host registration, and installation diagnosis."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import doctor
import specialists


class SpecialistTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = self.root / "upstream with spaces"
        self.source.mkdir()
        self.git("init", "--quiet")
        for name in ["testing", "using-agent-skills"]:
            path = self.source / "skills" / name / "SKILL.md"
            path.parent.mkdir(parents=True)
            path.write_text("---\nname: {}\ndescription: Test fixture.\n---\n\nUse the shared reference.\n".format(name))
        (self.source / "references").mkdir()
        (self.source / "references/shared.md").write_text("# Shared checklist\n")
        (self.source / "LICENSE").write_text("Fixture license\n")
        (self.source / "README.md").write_text("# Fixture\n")
        (self.source / "hooks").mkdir()
        (self.source / "hooks/hooks.json").write_text('{"should_not_ship": true}')
        self.commit()
        self.lock = {
            "repository": "https://github.com/example/fixture.git", "ref": "fixture",
            "commit": self.git("rev-parse", "HEAD").strip(), "version": "0.6.12",
            "skill_count": 1, "exclude": ["using-agent-skills"],
        }
        self.config = self.root / "config with spaces"
        self.core = self.root / "core skill"
        self.bundle = self.root / "bundle"

    def git(self, *args):
        git_env = dict(os.environ, GIT_AUTHOR_NAME="Fixture", GIT_AUTHOR_EMAIL="fixture@example.invalid",
                       GIT_COMMITTER_NAME="Fixture", GIT_COMMITTER_EMAIL="fixture@example.invalid")
        return subprocess.check_output(
            ["git", "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false", "-C", str(self.source), *args],
            env=git_env, text=True, stderr=subprocess.STDOUT,
        )

    def commit(self):
        self.git("add", ".")
        self.git("commit", "--quiet", "-m", "Fixture snapshot")

    def build(self):
        specialists.build_bundle(self.source, self.bundle, self.lock)

    def prepare_host(self, host):
        self.config.mkdir()
        shutil.copytree(ROOT / "skills/dev-flow", self.core)
        name = "AGENTS.md" if host == "codex" else "GEMINI.md"
        shutil.copy2(ROOT / "config/AGENTS.md", self.config / name)

    def report(self, host, required=False):
        with mock.patch.object(doctor, "load_lock", return_value=self.lock):
            return doctor.check_host(host, self.config, self.core, required)

    def test_bundle_uses_committed_bytes_and_keeps_shared_resources(self):
        original = (self.source / "skills/testing/SKILL.md").read_bytes()
        (self.source / "skills/testing/SKILL.md").write_text("Uncommitted replacement")
        (self.source / "skills/testing/untracked.md").write_text("Do not ship")
        self.build()
        self.assertEqual((self.bundle / "skills/testing/SKILL.md").read_bytes(), original)
        self.assertFalse((self.bundle / "skills/testing/untracked.md").exists())
        self.assertFalse((self.bundle / "skills/using-agent-skills").exists())
        self.assertFalse((self.bundle / "hooks").exists())
        self.assertEqual((self.bundle / "references/shared.md").read_bytes(),
                         (self.source / "references/shared.md").read_bytes())
        self.assertTrue((self.bundle / "LICENSE").is_file())
        self.assertEqual((self.bundle / "UPSTREAM-README.md").read_bytes(),
                         (self.source / "README.md").read_bytes())
        self.assertEqual(specialists.verify_bundle(self.bundle, self.lock), [])

    def test_wrong_commit_is_rejected_before_packaging(self):
        self.lock["commit"] = "0" * 40
        with self.assertRaisesRegex(ValueError, "commit mismatch"):
            self.build()
        self.assertFalse(self.bundle.exists())

    def test_upstream_symlink_is_rejected(self):
        (self.source / "skills/testing/link").symlink_to("../../LICENSE")
        self.commit()
        self.lock["commit"] = self.git("rev-parse", "HEAD").strip()
        with self.assertRaisesRegex(ValueError, "Unsupported archive entry"):
            self.build()

    def test_bundle_verification_detects_tampering_and_extra_files(self):
        self.build()
        (self.bundle / "skills/testing/SKILL.md").write_text("Changed instructions")
        (self.bundle / "hooks.json").write_text("{}")
        problems = specialists.verify_bundle(self.bundle, self.lock)
        self.assertTrue(any("skills/testing/SKILL.md" in p for p in problems))
        self.assertTrue(any("hooks.json" in p for p in problems))

    def test_replace_preserves_old_tree_and_is_idempotent(self):
        destination = self.root / "installed"
        destination.mkdir()
        (destination / "private.md").write_text("Original customization")
        self.build()
        specialists.replace_tree(self.bundle, destination, self.root / "backups")
        archived = list((self.root / "backups").glob("*/installed/private.md"))
        self.assertEqual(len(archived), 1)
        self.assertEqual(archived[0].read_text(), "Original customization")
        self.build()
        specialists.replace_tree(self.bundle, destination, self.root / "backups")
        self.assertEqual(len(list((self.root / "backups").iterdir())), 1)

    def test_replace_rejects_symlink_destination(self):
        original = self.root / "original"
        original.mkdir()
        (original / "keep").write_text("Keep")
        destination = self.root / "installed"
        destination.symlink_to(original)
        self.build()
        with self.assertRaisesRegex(ValueError, "regular directory"):
            specialists.replace_tree(self.bundle, destination, self.root / "backups")
        self.assertEqual((original / "keep").read_text(), "Keep")

    def test_codex_marketplace_keeps_plugin_inside_its_root(self):
        self.build()
        marketplace = self.root / "marketplace"
        specialists.build_marketplace(self.bundle, marketplace)
        catalog = json.loads((marketplace / ".agents/plugins/marketplace.json").read_text())
        target = marketplace / catalog["plugins"][0]["source"]["path"]
        self.assertTrue(target.resolve().is_relative_to(marketplace.resolve()))
        self.assertEqual(specialists.verify_bundle(target, self.lock), [])
        self.assertEqual(json.loads((target / ".codex-plugin/plugin.json").read_text())["skills"], "./skills/")

    def test_missing_codex_guidance_is_a_failure(self):
        self.prepare_host("codex")
        (self.config / "AGENTS.md").unlink()
        report = self.report("codex")
        self.assertFalse(report["ok"])
        self.assertTrue(any(c["check"] == "guidance" and c["status"] == "FAIL" for c in report["checks"]))

    def test_codex_override_is_checked_instead_of_shadowed_guidance(self):
        self.prepare_host("codex")
        (self.config / "AGENTS.override.md").write_text("# Different active instructions\n")
        self.assertFalse(self.report("codex")["ok"])

    def test_antigravity_duplicate_rule_is_a_failure(self):
        self.prepare_host("antigravity")
        rule = self.config / "rules/AGENTS.md"
        rule.parent.mkdir()
        shutil.copy2(self.config / "GEMINI.md", rule)
        self.assertFalse(self.report("antigravity")["ok"])
        rule.unlink()
        self.assertTrue(self.report("antigravity")["ok"])

    def test_missing_specialists_are_optional_until_required(self):
        self.prepare_host("antigravity")
        self.assertTrue(self.report("antigravity")["ok"])
        self.assertFalse(self.report("antigravity", required=True)["ok"])

    def test_disabled_antigravity_plugin_is_detected(self):
        self.prepare_host("antigravity")
        self.build()
        bundle = specialists.plugin_path("antigravity", self.config)
        bundle.parent.mkdir(parents=True)
        self.bundle.rename(bundle)
        self.assertTrue(self.report("antigravity", required=True)["ok"])
        (self.config / "config.json").write_text(json.dumps({"plugins": {"agent-skills": {"enabled": False}}}))
        self.assertFalse(self.report("antigravity", required=True)["ok"])

    def test_codex_requires_registration_and_verified_cache(self):
        self.prepare_host("codex")
        self.build()
        marketplace = self.config / specialists.MARKETPLACE
        specialists.build_marketplace(self.bundle, marketplace)
        self.assertFalse(self.report("codex", required=True)["ok"])
        (self.config / "config.toml").write_text(
            '[marketplaces.dev-flow-specialists]\nsource_type = "local"\nsource = ' + json.dumps(str(marketplace)) +
            '\n[plugins."agent-skills@dev-flow-specialists"]\nenabled = true\n'
        )
        self.assertFalse(self.report("codex", required=True)["ok"])
        cache = self.config / "plugins/cache/dev-flow-specialists/agent-skills/local"
        shutil.copytree(specialists.plugin_path("codex", self.config), cache)
        self.assertTrue(self.report("codex", required=True)["ok"])

    def test_codex_registration_uses_cli_and_preserves_settings_backup(self):
        self.config.mkdir()
        original = b'model = "configured-model"\n'
        (self.config / "config.toml").write_bytes(original)
        with mock.patch.object(specialists, "config_home", return_value=self.config), \
                mock.patch.object(specialists.shutil, "which", return_value="/bin/codex"), \
                mock.patch.object(specialists.subprocess, "run") as run:
            specialists.register_codex(self.config)
        self.assertEqual(run.call_args_list[0].args[0],
                         ["codex", "plugin", "marketplace", "add", str(self.config / specialists.MARKETPLACE)])
        self.assertEqual(run.call_args_list[1].args[0],
                         ["codex", "plugin", "add", "agent-skills@dev-flow-specialists"])
        backups = list((self.config / "backups").glob("*/config.toml"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), original)

    def test_codex_cache_must_match_current_packaged_source(self):
        self.prepare_host("codex")
        self.build()
        marketplace = self.config / specialists.MARKETPLACE
        specialists.build_marketplace(self.bundle, marketplace)
        source = specialists.plugin_path("codex", self.config)
        cache = self.config / "plugins/cache/dev-flow-specialists/agent-skills/local"
        shutil.copytree(source, cache)
        (self.config / "config.toml").write_text(
            '[marketplaces.dev-flow-specialists]\nsource_type = "local"\nsource = ' + json.dumps(str(marketplace)) +
            '\n[plugins."agent-skills@dev-flow-specialists"]\nenabled = true\n'
        )
        self.assertTrue(self.report("codex", required=True)["ok"])
        (source / "README.md").write_text("Updated packaging documentation\n")
        receipt = json.loads((source / specialists.RECEIPT).read_text())
        receipt["files"] = specialists.file_hashes(source)
        receipt["files"].pop(specialists.RECEIPT)
        specialists.write_json(source / specialists.RECEIPT, receipt)
        self.assertEqual(specialists.verify_bundle(source, self.lock), [])
        self.assertFalse(self.report("codex", required=True)["ok"])

    def test_doctor_json_cli_reports_missing_installation(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/doctor.py"), "--target", "codex", "--config-dir", str(self.config),
             "--skill-dir", str(self.core), "--json"], capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertFalse(json.loads(result.stdout)[0]["ok"])


if __name__ == "__main__":
    unittest.main()
