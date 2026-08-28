# Bersihin v2.0.1

Maintenance release for Bersihin v2.

## Fixed

- Fixed Python 3.9 runtime compatibility in ownership and temporary-file age checks.
- Fixed the PowerShell parser command used by GitHub Actions CI.
- Restored the complete standard MIT License text.

## CI

- Added `fail-fast: false` to the cross-platform Python matrix.
- Linux, Windows, and macOS jobs can now finish independently.
- CI validates Python 3.9 and Python 3.12.
- CI runs compile, unit-test, version, doctor, and dry-run checks.
- Bash installer/uninstaller syntax is validated.
- PowerShell installer/uninstaller syntax is validated.

## Upgrade

Installed copy:

```bash
bersihin --update
```

Git clone:

```bash
git pull
```

Then verify:

```bash
bersihin --version
bersihin --doctor
bersihin --dry-run
```

Expected version:

```text
2.0.1
```

## Requirements

- Python 3.9+
- Windows, Linux, Termux, WSL, macOS, BSD, or another supported Python-capable environment
