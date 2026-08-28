# Bersihin v2.0.0

Major cross-platform rewrite of Bersihin.

## Highlights

- Automatic Windows, Linux, Termux, WSL, macOS, BSD and POSIX detection.
- Native Python standard-library core with no third-party runtime dependencies.
- Safer allowlist-based cleanup.
- Dry-run and verbose candidate preview.
- Developer cache cleanup for Python/pip, npm, Yarn, pnpm, Go, Cargo, Composer, Gradle and NuGet.
- Optional browser cache cleanup.
- Optional Trash / Windows Recycle Bin cleanup.
- Optional package/system cache cleanup.
- Explicit aggressive mode for broad user caches.
- JSON output for automation.
- `--doctor` and `--list-targets` diagnostics.
- Self-update with syntax validation and local backup.
- Windows installer/uninstaller and Unix/Termux installer/uninstaller.
- Cross-platform GitHub Actions CI.

## Safety changes from v1

Bersihin no longer automatically runs `apt autoremove`, truncates system logs, wipes all of `/tmp`, or wipes all of `~/.cache` in the normal profile.

Run a preview first:

```bash
bersihin --dry-run --verbose
```

## Requirements

- Python 3.9+
- Windows, Linux, Termux, WSL, macOS, BSD, or another supported Python-capable environment

## Install

Linux / Termux / WSL / macOS:

```bash
curl -fsSL https://raw.githubusercontent.com/baska-pro/bersihin/main/install.sh | bash
```

Windows PowerShell:

```powershell
irm https://raw.githubusercontent.com/baska-pro/bersihin/main/install.ps1 | iex
```
