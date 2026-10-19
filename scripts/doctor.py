#!/usr/bin/env python3
"""Read-only checks for dev-flow installation, global guidance and specialists."""
import argparse
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
from specialists import MARKETPLACE, PLUGIN, ROOT, config_home, file_hashes, load_lock, plugin_path, verify_bundle


def toml_section(text, name):
    """Read only the sections owned by the Codex CLI, without rewriting user TOML."""
    active = False
    values = {}
    for line in text.splitlines():
        header = re.fullmatch(r"\s*\[([^\[\]]+)\]\s*(?:#.*)?", line)
        if header:
            active = header.group(1).replace('"', '') == name
        elif active and "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def check_host(host, config, skill, require_specialists=False):
    checks = []

    def add(status, name, detail):
        checks.append({"status": status, "check": name, "detail": str(detail)})

    source = ROOT / "skills/dev-flow"
    try:
        expected = file_hashes(source)
        actual = file_hashes(skill)
        changed = sorted(name for name in set(expected) | set(actual) if expected.get(name) != actual.get(name))
        if changed:
            add("FAIL", "core", "Missing, extra or changed skill files: " + ", ".join(changed))
        else:
            add("PASS", "core", "{} files match {}".format(len(expected), skill))
    except (OSError, ValueError) as error:
        add("FAIL", "core", error)

    names = ["AGENTS.override.md", "AGENTS.md"] if host == "codex" else ["GEMINI.md", "AGENTS.md"]
    guidance = [config / name for name in names if (config / name).is_file() and (config / name).stat().st_size]
    if not guidance:
        add("FAIL", "guidance", "Missing non-empty global guidance in " + str(config))
    else:
        active = guidance[:1] if host == "codex" else guidance
        template = (ROOT / "config/AGENTS.md").read_bytes()
        for path in active:
            content = path.read_bytes()
            if content == template:
                add("PASS", "guidance", path)
            elif b"dev-flow" in content:
                add("WARN", "guidance", "Custom guidance references dev-flow; review proposals manually: " + str(path))
            else:
                add("FAIL", "guidance", "Active guidance does not reference dev-flow: " + str(path))
        if host == "codex" and active[0].name == "AGENTS.override.md":
            add("WARN", "override", "AGENTS.override.md takes precedence over AGENTS.md")

    if host == "antigravity":
        candidates = guidance + list((config / "rules").glob("*.md"))
        if config.resolve() == (Path.home() / ".gemini/config").resolve():
            candidates += [Path.home() / ".gemini" / name for name in ["AGENTS.md", "GEMINI.md"]]
        seen = {}
        for path in candidates:
            if path.is_file() and path.stat().st_size:
                content = path.read_bytes()
                if content in seen and seen[content].resolve() != path.resolve():
                    add("FAIL", "duplicate-rule", "{} duplicates {}".format(path, seen[content]))
                else:
                    seen[content] = path
        if not any(c["check"] == "duplicate-rule" for c in checks):
            add("PASS", "duplicate-rule", "No identical global rule copies")

    bundle = plugin_path(host, config)
    if not bundle.exists():
        add("FAIL" if require_specialists else "WARN", "specialists", "Optional specialist bundle is absent: " + str(bundle))
    else:
        problems = verify_bundle(bundle, load_lock())
        for problem in problems:
            add("FAIL", "specialists", problem)
        if not problems:
            add("PASS", "specialists", "{} skills match pinned bundle {}".format(load_lock()["skill_count"], load_lock()["commit"]))
        try:
            if host == "antigravity":
                settings_path = config / "config.json"
                settings = json.loads(settings_path.read_text()) if settings_path.exists() else {}
                enabled = settings.get("plugins", {}).get(PLUGIN, {}).get("enabled", True)
                if not enabled:
                    add("FAIL", "plugin-enabled", "Antigravity specialist plugin is disabled")
                else:
                    add("PASS", "plugin-enabled", "Antigravity specialist plugin is enabled")
            else:
                settings_path = config / "config.toml"
                text = settings_path.read_text() if settings_path.exists() else ""
                registration = toml_section(text, "plugins." + PLUGIN + "@" + MARKETPLACE)
                marketplace = toml_section(text, "marketplaces." + MARKETPLACE)
                if registration.get("enabled") != "true":
                    add("FAIL", "plugin-enabled", "Codex specialist plugin is not enabled through the CLI")
                else:
                    add("PASS", "plugin-enabled", "Codex specialist plugin is enabled")
                try:
                    raw_source = marketplace.get("source", '""')
                    source_path = raw_source[1:-1] if raw_source.startswith("'") else json.loads(raw_source)
                    registered = Path(source_path).resolve() == (config / MARKETPLACE).resolve()
                except (ValueError, TypeError):
                    registered = False
                if not registered:
                    add("FAIL", "marketplace", "Codex marketplace does not point at the installed bundle")
                else:
                    add("PASS", "marketplace", config / MARKETPLACE)
                cache = config / "plugins/cache" / MARKETPLACE / PLUGIN
                copies = [p for p in cache.glob("*") if p.is_dir()]
                expected_cache = file_hashes(bundle)
                verified = [p for p in copies if not verify_bundle(p, load_lock()) and file_hashes(p) == expected_cache]
                if not verified:
                    add("FAIL", "plugin-cache", "Codex has no verified installed cache copy; run codex plugin add")
                else:
                    add("PASS", "plugin-cache", verified[0])
        except (OSError, ValueError, TypeError, AttributeError) as error:
            add("FAIL", "host-settings", "Cannot verify host settings: {}".format(error))
    return {"host": host, "checks": checks, "ok": not any(c["status"] == "FAIL" for c in checks)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=["all", "codex", "antigravity"], default="all")
    parser.add_argument("--config-dir", type=Path)
    parser.add_argument("--skill-dir", type=Path)
    parser.add_argument("--require-specialists", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.target == "all" and (args.config_dir or args.skill_dir):
        parser.error("Use a single --target with explicit destinations")
    hosts = ["codex", "antigravity"] if args.target == "all" else [args.target]
    reports = []
    try:
        for host in hosts:
            config = (args.config_dir or config_home(host)).expanduser().absolute()
            skill = args.skill_dir or (Path.home() / ".agents/skills/dev-flow" if host == "codex" else config / "skills/dev-flow")
            reports.append(check_host(host, config, skill.expanduser().absolute(), args.require_specialists))
    except (OSError, ValueError) as error:
        parser.exit(1, "Installation check failed: {}\n".format(error))
    if args.json:
        print(json.dumps(reports, indent=2))
    else:
        for report in reports:
            print(report["host"] + ":")
            for item in report["checks"]:
                print("  {status} {check}: {detail}".format(**item))
    return 0 if all(report["ok"] for report in reports) else 1


if __name__ == "__main__":
    raise SystemExit(main())
