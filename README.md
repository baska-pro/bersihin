# Bersihin 🧼

<p align="center">
  <strong>Safe, informative cross-platform cleaner for temporary files and development caches.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-2.0.2-111827?style=flat-square" alt="Version 2.0.2">
  <img src="https://img.shields.io/badge/Python-3.9%2B-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/Windows-supported-0078D4?style=flat-square&logo=windows11&logoColor=white" alt="Windows">
  <img src="https://img.shields.io/badge/Linux-supported-FCC624?style=flat-square&logo=linux&logoColor=111827" alt="Linux">
  <img src="https://img.shields.io/badge/Termux-supported-111827?style=flat-square" alt="Termux">
  <img src="https://img.shields.io/badge/license-MIT-16A34A?style=flat-square" alt="MIT">
  <a href="https://github.com/baska-pro/bersihin/actions/workflows/ci.yml"><img src="https://github.com/baska-pro/bersihin/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
</p>

<p align="center">
  <a href="./README.id.md">Bahasa Indonesia</a> ·
  <a href="./docs/INSTALL.md">Install</a> ·
  <a href="./docs/SAFETY.md">Safety</a> ·
  <a href="./docs/PLATFORMS.md">Platforms</a> ·
  <a href="./CHANGELOG.md">Changelog</a>
</p>

---

## Overview

**Bersihin** automatically detects Windows, Linux, Termux, WSL, macOS, BSD and other POSIX-like environments and builds a conservative cleanup plan for the current platform.

The current `main` development state keeps the public version at **2.0.2** while improving the cleaner experience. The published v2 safety model is unchanged: Bersihin does not blindly wipe `/tmp`, the whole user cache, system logs, installed packages, or Docker data.

## Highlights

- automatic platform detection;
- responsive realtime progress for interactive terminals;
- smooth percentage progress instead of a fast spinner;
- compact Termux/phone layout and wider desktop layout;
- detailed scan counters: checked, matched, eligible, too-new and skipped/pruned;
- summary by target/category and reclaimable size;
- automatic project-cache discovery;
- Python/pip, npm/npx, Yarn, pnpm, Go, Cargo, Composer, Gradle and related development caches;
- optional browser-cache cleanup;
- optional Trash / Recycle Bin cleanup;
- opt-in system/package cache cleanup;
- opt-in broad user-cache cleanup;
- `--full` profile for a broader opt-in scan;
- age filtering with `--older-than`;
- JSON output for automation;
- `--doctor` and `--list-targets` diagnostics;
- no third-party Python runtime dependency.

## Install

### Windows

```powershell
irm https://raw.githubusercontent.com/baska-pro/bersihin/main/install.ps1 | iex
```

Or from a clone:

```powershell
.\install.ps1
```

### Linux / Termux / WSL / macOS

Quick install:

```bash
curl -fsSL https://raw.githubusercontent.com/baska-pro/bersihin/main/install.sh | bash
```

`curl` without `| bash` only prints the installer; it does not install Bersihin.

From a clone:

```bash
git clone https://github.com/baska-pro/bersihin.git
cd bersihin
chmod +x install.sh
./install.sh
```

Verify:

```bash
bersihin --version
bersihin --doctor
bersihin --dry-run
```

## Usage

Normal cleanup:

```bash
bersihin
```

Safe preview:

```bash
bersihin --dry-run
```

Include fresh age-filtered entries:

```bash
bersihin --older-than 0 --dry-run
```

Broader opt-in preview:

```bash
bersihin --full --dry-run
```

Optional scopes:

```bash
bersihin --system --dry-run
bersihin --trash --dry-run
bersihin --browsers --dry-run
bersihin --aggressive --dry-run
```

Only selected categories:

```bash
bersihin --category temp --dry-run
bersihin --category dev --dry-run
```

Detailed candidate paths and hidden/missing targets:

```bash
bersihin --dry-run --verbose
```

Disable interactive progress:

```bash
bersihin --no-progress
```

Force ANSI progress when TTY detection is unusual:

```bash
bersihin --force-progress --dry-run
```

Machine-readable output:

```bash
bersihin --dry-run --json
```

Diagnostics:

```bash
bersihin --doctor
bersihin --list-targets
```

Update/uninstall:

```bash
bersihin --update
bersihin --uninstall
```

## Realtime Progress

On an interactive terminal, Bersihin displays a progress bar on the same terminal line while it scans:

```text
[====>           ]  28% Project cache | 10/36 | chk 124 | 83 ms
[==========>     ]  67% npm cache     | 24/36 | chk 382 | 410 ms
[================] 100% Finalizing scan
```

On narrow terminals such as Termux, labels are shortened before counters are removed. On non-interactive output, JSON mode, or `--no-progress`, animation is disabled.

Fast scans may finish internally in a few hundred milliseconds. Interactive display is intentionally smoothed briefly so progress remains visible to a human without slowing automation/JSON mode.

## Safety Defaults

The default profile intentionally avoids:

- filesystem roots and the home directory itself;
- symlink traversal;
- other users' POSIX temporary entries;
- system logs;
- package autoremove;
- Docker prune;
- browser caches unless explicitly requested;
- Trash/Recycle Bin unless explicitly requested;
- broad generic user caches unless explicitly requested.

Use `--full`, `--system`, `--trash`, `--browsers`, or `--aggressive` only after a dry run when needed.

See [docs/SAFETY.md](./docs/SAFETY.md).

## Platform Behavior

| Environment | Detection | Default behavior |
|---|---|---|
| Windows | native Windows/Python | user temp + known development caches |
| Linux | kernel + `/etc/os-release` | owned old temp + user/development caches |
| Termux | `$PREFIX` + Termux filesystem markers | Termux temp + dev caches + package archives |
| WSL | Microsoft kernel/WSL environment | Linux/WSL temp + development caches |
| macOS | Darwin | user temp + development caches |
| BSD/POSIX | platform fallback | conservative temp + user development caches |

## Development Status

The current repository `main` still reports version **2.0.2**. Feature work in `main` is tracked under **Unreleased** in `CHANGELOG.md`; the version should be bumped only when the next release is finalized.

## License

MIT License. See [LICENSE](./LICENSE).

Copyright © 2026 Baska ID.
