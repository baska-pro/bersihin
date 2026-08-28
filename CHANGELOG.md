# Changelog

## 2.0.1 - 2026-08-28

### Fixed

- Fixed Python 3.9 compatibility in file ownership and age checks by using
  `os.stat(..., follow_symlinks=False)` instead of the newer `Path.stat()`
  keyword argument.
- Fixed GitHub Actions PowerShell syntax-validation step.
- Restored the complete standard MIT License text.

### Changed

- GitHub Actions matrix now uses `fail-fast: false` so one failed platform does
  not cancel the remaining Windows, Linux, or macOS validation jobs.
- Added regression coverage for the POSIX ownership helper.

## 2.0.0 - 2026-08-28

### Added

- Native Python cross-platform core.
- Automatic Windows, Linux, Termux, WSL, macOS, BSD and POSIX detection.
- `--doctor` diagnostics.
- `--json` scan output.
- `--older-than` temporary-file age filter.
- Optional `--system`, `--trash`, `--browsers`, and `--aggressive` scopes.
- Windows Recycle Bin API integration.
- Windows PowerShell installer/uninstaller.
- Unix/Termux installer/uninstaller.
- Python package metadata (`pyproject.toml`).
- GitHub Actions cross-platform syntax/smoke tests.

### Changed

- Replaced the Bash-only cleaner with a standard-library Python implementation.
- Default cleaning is now allowlist-based and conservative.
- Update URL moved to `baska-pro/bersihin`.
- Installer no longer tries to delete the source/clone directory.

### Removed / Safety Changes

- Removed automatic `apt autoremove`.
- Removed blanket truncation of system logs.
- Removed blanket deletion of `/tmp` and `~/.cache` from the default profile.
- Removed dependency on GNU-only `du -sb` / `numfmt` for size reporting.

## 1.x

Original Bash implementation for Termux/Linux with package/language/system cache cleaning, dry-run, update and uninstall support.
