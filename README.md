# Bersihin 🧼

<p align="center">
  <strong>Safe cross-platform cleaner for developer caches and temporary files.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-2.0.1-111827?style=flat-square" alt="Version 2.0.1">
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
  <a href="./docs/MIGRATION_V1.md">Migration v1</a> ·
  <a href="./CHANGELOG.md">Changelog</a>
</p>

---

## Overview

**Bersihin** automatically detects Windows, Linux, Termux, WSL, macOS, BSD and other POSIX-like environments, then builds a cleanup plan appropriate for that platform.

Version 2 is a rewrite focused on **safer cleanup**.

> **v2.0.1 maintenance release:** fixes Python 3.9 runtime compatibility, GitHub Actions PowerShell validation, and restores the complete MIT License text. It does not blindly wipe `/tmp`, `~/.cache`, system logs, or package-manager data. Default cleanup targets known temporary/development caches, uses age limits for temp files, avoids symlinks and protected roots, and asks for confirmation before deletion.

## Highlights

- automatic platform detection;
- Windows / Linux / Termux / WSL / macOS / BSD awareness;
- safe dry-run/scan mode;
- Python, pip, npm, Yarn, pnpm, Go, Cargo, Composer, Gradle and NuGet cache awareness;
- optional browser cache cleanup;
- optional Trash / Recycle Bin cleanup;
- opt-in system package-cache cleanup;
- opt-in aggressive user-cache cleanup;
- minimum-age filter for temporary files;
- user-ownership filtering for shared POSIX temp directories;
- JSON scan output for automation;
- built-in platform diagnostics (`--doctor`);
- self-update from GitHub with syntax validation and backup;
- Windows PowerShell installer and Unix/Termux installer;
- no third-party Python runtime dependency.

## Safety Defaults

Bersihin intentionally does **not** run risky package operations such as `apt autoremove`, delete logs, delete application data, or run Docker system prune automatically.

Extra scopes must be explicitly requested:

```text
--system      system/package download caches
--trash       Trash / Windows Recycle Bin
--browsers    browser cache only
--aggressive  broad user cache directories
```

Read [docs/SAFETY.md](./docs/SAFETY.md) before using aggressive/system modes.

## Install

### Windows

Quick install from PowerShell:

```powershell
irm https://raw.githubusercontent.com/baska-pro/bersihin/main/install.ps1 | iex
```

Or clone/download the repository and run:

```powershell
.\install.ps1
```

or double-click:

```text
install.cmd
```

### Linux / Termux / WSL / macOS

Quick install:

```bash
curl -fsSL https://raw.githubusercontent.com/baska-pro/bersihin/main/install.sh | bash
```

Or from a clone:

```bash
chmod +x install.sh
./install.sh
```

### Git clone

```bash
git clone https://github.com/baska-pro/bersihin.git
cd bersihin
```

More: [Installation Guide](./docs/INSTALL.md)

## Usage

First inspect the detected environment:

```bash
bersihin --doctor
```

Safe preview:

```bash
bersihin --dry-run
```

Normal cleanup (asks for confirmation):

```bash
bersihin
```

Non-interactive cleanup:

```bash
bersihin --yes
```

Optional scopes:

```bash
bersihin --browsers --dry-run
bersihin --trash --dry-run
bersihin --system --dry-run
bersihin --aggressive --dry-run
```

Only selected categories:

```bash
bersihin --category temp --dry-run
bersihin --category dev --dry-run
```

Temporary-file age threshold:

```bash
bersihin --older-than 7 --dry-run
```

Show every candidate path:

```bash
bersihin --dry-run --verbose
```

Show selected cleanup roots/rules:

```bash
bersihin --list-targets
```

Machine-readable scan:

```bash
bersihin --dry-run --json
```

Update / uninstall:

```bash
bersihin --update
bersihin --uninstall
```

## Platform Behavior

| Environment | Detection | Default scope |
|---|---|---|
| Windows | native Windows/Python | user temp + development caches |
| Linux | kernel + `/etc/os-release` | owned old temp + development caches |
| Termux | `$PREFIX`, Termux paths | Termux tmp + dev caches + Termux package archives |
| WSL | Microsoft kernel/WSL env | Linux/WSL temp + development caches |
| macOS | Darwin | user temp + development caches |
| BSD/POSIX | platform fallback | conservative temp + user development caches |

## Update Workflow

For a Git clone:

```bash
git pull
```

For installed standalone copies:

```bash
bersihin --update
```

The built-in updater downloads `bersihin.py`, validates that it compiles, creates a `.bak` copy, and only then replaces the installed source.

## Project Structure

```text
bersihin/
├── bersihin.py
├── install.sh
├── install.ps1
├── install.cmd
├── uninstall.sh
├── uninstall.ps1
├── pyproject.toml
├── requirements.txt
├── README.md
├── README.id.md
├── CHANGELOG.md
├── SECURITY.md
├── CONTRIBUTING.md
├── LICENSE
├── VERSION
├── docs/
├── tests/
└── .github/
```

## License

MIT License. See [LICENSE](./LICENSE).

Copyright © 2026 Baska ID.

Maintained at [@baska-pro](https://github.com/baska-pro).
