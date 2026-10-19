# Dev Flow for macOS — Codex & Antigravity App

Personal development workflow with a primary `dev-flow` skill, global working agreements, and optional specialist skills selected on demand. It supports multiple programming stacks through 14 references; it does not load every reference or an entire development lifecycle for each task.

This installer targets **Codex** and **Google Antigravity App/IDE** on macOS. Antigravity CLI has a separate configuration layout and is not installed by `--antigravity`.

## Prerequisites

- macOS with Git and Python 3.9 or newer: verify `git --version` and `python3 --version`.
- The host application you want to configure, installed and authenticated separately.
- For Codex specialist installation, a current `codex` CLI in PATH with `plugin marketplace add` and `plugin add` support.
- Network access only when downloading the optional pinned specialists. Core installation and `doctor.py` are offline.

The installer does not install system packages, change model or permission settings, or handle credentials. Install Codex using [OpenAI's setup instructions](https://learn.chatgpt.com/docs/codex-cli). Refer to [Google's skills documentation](https://antigravity.google/docs/skills) for Antigravity surfaces and locations.

## Install

```bash
mkdir -p "$HOME/Developer"
git clone https://github.com/tuanminh2409bn/dev-flow-macos.git "$HOME/Developer/dev-flow-macos"
cd "$HOME/Developer/dev-flow-macos"

./install.sh                 # Codex core
./install.sh --antigravity   # Antigravity App core
```

Run both commands to configure both applications. Default destinations:

| Component | Codex | Antigravity App |
| --- | --- | --- |
| Global guidance | `~/.codex/AGENTS.md` | `~/.gemini/config/GEMINI.md` |
| Primary skill | `~/.agents/skills/dev-flow` | `~/.gemini/config/skills/dev-flow` |
| Backups | `~/.codex/backups/` | `~/.gemini/config/backups/` |

`CODEX_HOME` and `GEMINI_CONFIG_DIR` override the corresponding config directory. Codex's user skill directory remains `~/.agents/skills`. Explicit `--config-dir`, `--skill-dir`, and `--guidance-name` support isolated core tests and deliberate custom layouts; they do not change where a host discovers files.

Existing guidance that differs from the template is preserved; the installer writes a uniquely named `*.proposed-*` for review. Merge desired changes while keeping machine-specific rules. Codex's `AGENTS.override.md`, when present, takes precedence over `AGENTS.md`; doctor reports this override.

For Antigravity, the installer keeps one global `GEMINI.md`. A regular `rules/AGENTS.md` with identical contents is moved into the backup directory. Custom or symlinked rules are preserved. It never creates another copy of global guidance in `rules/`.

## Optional specialists for either application

`dev-flow` works independently. To add its specialist workflows:

```bash
./install.sh --with-specialists
./install.sh --antigravity --with-specialists
```

Both hosts receive the same 24 specialist skills from [Addy Osmani's Agent Skills](https://github.com/addyosmani/agent-skills), pinned by [config/specialists.lock.json](config/specialists.lock.json): tag `0.6.12`, commit `a06bc63b3f8b829c14b0bbf53d99fefc39d58092`. The installer verifies the commit, reads committed Git objects, and preserves shared references and the upstream license. `using-agent-skills` is excluded to keep `dev-flow` as the primary router. Upstream hooks, commands and agents are not installed or executed.

- **Codex:** creates a skills-only local marketplace under `~/.codex/dev-flow-specialists/`, then registers and installs `agent-skills@dev-flow-specialists` using Codex CLI. Codex settings are backed up before registration; existing marketplaces and unrelated settings remain managed by Codex. Avoid also enabling another copy of the same specialist bundle.
- **Antigravity App:** stages the plugin at `~/.gemini/config/plugins/agent-skills/`; an existing plugin is backed up before replacement. Existing enable/disable preferences are preserved.

Installed bundles include a provenance receipt and file hashes for offline integrity checks. The displayed README describes this selected package; original upstream documentation is preserved as `UPSTREAM-README.md`. Codex's installed cache must match the current packaged source. No token, speed or cost saving is claimed without a benchmark.

To avoid downloading twice, use an existing Git checkout at the exact locked commit:

```bash
./install.sh --with-specialists --specialists-source /absolute/path/to/agent-skills
./install.sh --antigravity --with-specialists --specialists-source /absolute/path/to/agent-skills
```

The source checkout's uncommitted and untracked files are not packaged. A different HEAD is rejected. Specialist registration for Codex uses its active config directory; custom destinations are intended for isolated core checks, not another Codex profile's plugin installation.

## Verify and update

```bash
python3 scripts/doctor.py                         # Both hosts; specialists optional
python3 scripts/doctor.py --require-specialists   # Both hosts with pinned specialists
python3 scripts/doctor.py --target codex --json   # Machine-readable report
```

Doctor is read-only and returns a nonzero status for missing/changed skill files, missing active guidance or routing, duplicate global rules, broken bundle integrity, a disabled managed plugin, or missing Codex registration/cache. It verifies the managed bundle from this installer; it does not audit every third-party plugin on the machine. Custom guidance referencing `dev-flow` is reported for manual review.

After installation, open a new chat so global guidance is rebuilt. If a new plugin does not appear, restart the host when existing work permits. In Antigravity, check **Customizations → Installed** for `/dev-flow`, one global guidance entry, and the specialist plugin. In Codex, inspect `/skills` or the skill selector and `codex plugin list`. Doctor checks files and registration; the host's skill selector confirms discovery, and a real task is needed to test behavior.

To update, run `git pull --ff-only` in this repository and repeat the install commands for **each** host you use. Include `--with-specialists` when updating the managed bundle, then run doctor. Preserve and review any guidance proposals. Do not overwrite an entire config file to restore one plugin.

## Stack references

The primary skill selects references from workspace manifests and actual repository scripts:

- [Flutter/Dart](skills/dev-flow/references/flutter.md), [Swift/Apple](skills/dev-flow/references/swift.md), [JVM/Android](skills/dev-flow/references/jvm.md)
- [Next.js](skills/dev-flow/references/nextjs.md), [TypeScript/JavaScript](skills/dev-flow/references/typescript-js.md), [Python](skills/dev-flow/references/python.md)
- [Go](skills/dev-flow/references/go.md), [Rust](skills/dev-flow/references/rust.md), [.NET](skills/dev-flow/references/dotnet.md), [C/C++](skills/dev-flow/references/cpp.md), [Ruby/PHP/Elixir](skills/dev-flow/references/ruby-php-elixir.md)
- [Data/contracts](skills/dev-flow/references/data-and-contracts.md), [Platform discovery](skills/dev-flow/references/platforms.md), [Specialist routing](skills/dev-flow/references/specialists.md)

Keep project-specific `AGENTS.md` or `GEMINI.md` in each project's own repository. See [the historical assessment](docs/dev-flow-assessment-2026-10-12.md) for earlier design decisions; its installation snapshots are not evidence of the current machine state.

## Development checks

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
/bin/bash -n install.sh
git diff --check
```

Tests use temporary destinations and local Git fixtures. They cover duplicate-rule migration, custom guidance, backups, symlink rejection, immutable-source packaging, integrity checks, disabled plugins and Codex registration/cache diagnosis. GitHub Actions runs the suite on macOS. Authentication, sessions, logs, plugin caches and API keys are excluded from this repository.
