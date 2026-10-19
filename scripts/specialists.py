#!/usr/bin/env python3
"""Install a pinned, skills-only specialist bundle for Codex or Antigravity App."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MARKETPLACE = "dev-flow-specialists"
PLUGIN = "agent-skills"
RECEIPT = ".dev-flow-source.json"


def load_lock():
    return json.loads((ROOT / "config/specialists.lock.json").read_text())


def config_home(host):
    if host == "codex":
        return Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex").expanduser()
    return Path(os.environ.get("GEMINI_CONFIG_DIR") or Path.home() / ".gemini/config").expanduser()


def plugin_path(host, config):
    if host == "codex":
        return config / MARKETPLACE / "plugins" / PLUGIN
    return config / "plugins" / PLUGIN


def file_hashes(directory):
    result = {}
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            raise ValueError("Unexpected symlink: {}".format(path))
        if path.is_file() and path.name != ".DS_Store":
            result[path.relative_to(directory).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def build_bundle(source, destination, lock):
    """Read committed Git objects, never executable upstream installers or hooks."""
    actual = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
    if actual != lock["commit"]:
        raise ValueError("Upstream commit mismatch: expected {}, got {}".format(lock["commit"], actual))
    archive = subprocess.check_output([
        "git", "-C", str(source), "archive", "--format=tar", actual,
        "skills", "references", "LICENSE", "README.md",
    ])
    destination.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(archive)) as package:
        for member in package.getmembers():
            relative = PurePosixPath(member.name)
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError("Unsafe archive path: {}".format(member.name))
            if member.isdir():
                continue
            if not member.isfile():
                raise ValueError("Unsupported archive entry: {}".format(member.name))
            if relative.parts[0] == "skills" and relative.parts[1] in lock["exclude"]:
                continue
            target = destination.joinpath(*relative.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with package.extractfile(member) as data:
                target.write_bytes(data.read())
            target.chmod(0o755 if member.mode & 0o111 else 0o644)
    skills = sorted(p.parent.name for p in (destination / "skills").glob("*/SKILL.md"))
    if len(skills) != lock["skill_count"]:
        raise ValueError("Expected {} specialist skills, found {}".format(lock["skill_count"], len(skills)))
    (destination / "README.md").rename(destination / "UPSTREAM-README.md")
    (destination / "README.md").write_text(
        "# Dev Flow Specialist Skills\n\n"
        "{} optional engineering workflows, selected on demand by `dev-flow`.\n\n"
        "Browse the Skills tab or your host's skill selector. Select a specialist by its name, "
        "for example `test-driven-development` or `debugging-and-error-recovery`.\n\n"
        "This package contains the listed skills and their shared references. It omits the "
        "`using-agent-skills` meta-router, lifecycle command wrappers, hooks and subagents. "
        "Keep `dev-flow` as the primary workflow; load a specialist for a concrete need.\n\n"
        "Source: [Addy Osmani Agent Skills {}]({}/tree/{}), pinned to commit `{}`.\n\n"
        "The [upstream README](UPSTREAM-README.md) describes the full upstream repository, "
        "including components outside this selected package. [License](LICENSE).\n".format(
            len(skills), lock["version"], lock["repository"].removesuffix(".git"),
            lock["commit"], lock["commit"],
        )
    )
    description = "Specialist engineering workflows selected on demand by dev-flow."
    write_json(destination / "plugin.json", {
        "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
        "name": PLUGIN, "version": lock["version"],
        "description": description,
    })
    write_json(destination / ".codex-plugin/plugin.json", {
        "name": PLUGIN, "version": lock["version"],
        "description": description, "skills": "./skills/",
    })
    write_json(destination / RECEIPT, {
        "upstream": lock, "skills": skills, "files": file_hashes(destination),
    })


def verify_bundle(directory, lock):
    """Check provenance and all packaged bytes without network access."""
    try:
        receipt = json.loads((directory / RECEIPT).read_text())
        if receipt["upstream"] != lock:
            return ["Specialist provenance differs from config/specialists.lock.json"]
        actual = file_hashes(directory)
        actual.pop(RECEIPT, None)
        expected = receipt["files"]
        changed = sorted(name for name in set(actual) | set(expected) if actual.get(name) != expected.get(name))
        skills = sorted(p.parent.name for p in (directory / "skills").glob("*/SKILL.md"))
        problems = ["Specialist file differs or is missing: " + name for name in changed]
        if skills != receipt["skills"] or len(skills) != lock["skill_count"]:
            problems.append("Specialist skill inventory differs from the pinned bundle")
        if any((directory / "skills" / name).exists() for name in lock["exclude"]):
            problems.append("Excluded meta-router is installed")
        return problems
    except (OSError, ValueError, KeyError, TypeError) as error:
        return ["Cannot verify specialist bundle: {}".format(error)]


def build_marketplace(bundle, destination):
    target = destination / "plugins" / PLUGIN
    target.parent.mkdir(parents=True)
    shutil.move(str(bundle), str(target))
    write_json(destination / ".agents/plugins/marketplace.json", {
        "name": MARKETPLACE,
        "interface": {"displayName": "Dev Flow Specialists"},
        "plugins": [{
            "name": PLUGIN, "source": {"source": "local", "path": "./plugins/" + PLUGIN},
            "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
            "category": "Productivity",
        }],
    })


def replace_tree(stage, destination, backups):
    if destination.is_symlink() or (destination.exists() and not destination.is_dir()):
        raise ValueError("Destination must be a regular directory: {}".format(destination))
    if destination.exists() and file_hashes(stage) == file_hashes(destination):
        print("Specialist bundle already matches: {}".format(destination))
        return
    previous = None
    if destination.exists():
        backups.mkdir(parents=True, exist_ok=True)
        previous = Path(tempfile.mkdtemp(prefix="dev-flow-specialists-", dir=str(backups))) / destination.name
        destination.rename(previous)
        print("Previous specialist bundle backed up to: {}".format(previous))
    try:
        stage.rename(destination)
    except OSError:
        if previous is not None:
            previous.rename(destination)
        raise


def register_codex(config):
    if config.resolve() != config_home("codex").resolve():
        raise ValueError("Codex registration requires its active CODEX_HOME; custom directories are for isolated core checks")
    if shutil.which("codex") is None:
        raise ValueError("Codex CLI is required to register the specialist plugin")
    settings = config / "config.toml"
    if settings.exists():
        backup_root = config / "backups"
        backup_root.mkdir(parents=True, exist_ok=True)
        backup = Path(tempfile.mkdtemp(prefix="dev-flow-plugin-config-", dir=str(backup_root)))
        shutil.copy2(settings, backup / "config.toml")
        print("Codex settings backed up to: {}".format(backup))
    subprocess.run(["codex", "plugin", "marketplace", "add", str(config / MARKETPLACE)], check=True)
    subprocess.run(["codex", "plugin", "add", PLUGIN + "@" + MARKETPLACE], check=True)


def install(host, config, source, lock):
    if host == "codex" and config.resolve() != config_home("codex").resolve():
        raise ValueError("Use the active CODEX_HOME for Codex specialist registration")
    if host == "codex" and shutil.which("codex") is None:
        raise ValueError("Codex CLI is required to register the specialist plugin")
    destination = config / MARKETPLACE if host == "codex" else plugin_path(host, config)
    if destination.is_symlink() or (destination.exists() and not destination.is_dir()):
        raise ValueError("Destination must be a regular directory: {}".format(destination))
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".dev-flow-specialists-", dir=str(destination.parent)) as temporary:
        staging = Path(temporary)
        bundle = staging / "bundle"
        build_bundle(source, bundle, lock)
        if host == "codex":
            replacement = staging / "marketplace"
            build_marketplace(bundle, replacement)
        else:
            replacement = bundle
        replace_tree(replacement, destination, config / "backups")
    if host == "codex":
        register_codex(config)
    print("Installed {} pinned specialists for {}".format(lock["skill_count"], host))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=["codex", "antigravity"], required=True)
    parser.add_argument("--config-dir", type=Path)
    parser.add_argument("--source-dir", type=Path, help="Existing Git checkout at the locked commit; reads committed objects only")
    args = parser.parse_args()
    lock = load_lock()
    config = (args.config_dir or config_home(args.target)).expanduser().absolute()
    try:
        if args.source_dir:
            install(args.target, config, args.source_dir, lock)
        else:
            with tempfile.TemporaryDirectory(prefix="dev-flow-upstream-") as temporary:
                source = Path(temporary) / "source"
                subprocess.run([
                    "git", "-c", "core.hooksPath=/dev/null", "clone", "--depth", "1",
                    "--branch", lock["ref"], lock["repository"], str(source),
                ], check=True)
                install(args.target, config, source, lock)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, "Specialist installation failed: {}\n".format(error))


if __name__ == "__main__":
    main()
