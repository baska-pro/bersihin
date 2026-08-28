# Changelog

## Unreleased

### Added

- Realtime progress rendering for interactive terminals.
- Smooth percentage progress bar designed for narrow Termux/mobile terminals.
- `--full` profile for enabling the broader opt-in cleanup scopes together.
- `--no-progress` / `--quiet` for disabling interactive progress.
- `--force-progress` for terminals where TTY detection is unreliable.
- Detailed scan accounting for checked, matched, eligible, too-new, skipped/pruned and error entries.
- Automatic project-cache discovery with project-specific Python/Node/build-cache rules.
- Richer scan and cleanup summaries, including reclaimable-by-target/category information.

### Changed

- Fast interactive scans keep the visual progress visible briefly instead of flashing from 0% to 100%.
- Missing/unavailable targets are hidden from normal output and summarized; `--verbose` shows them.
- Narrow-terminal output preserves counters and durations before labels.
- Project traversal prunes known large/unnecessary directories such as repository metadata and dependency/build trees where appropriate.
- Cleanup progress uses the same responsive progress renderer as scanning.
- Very short durations are displayed in milliseconds.

### Safety

- Default cleanup remains conservative and allowlist-based.
- Browser, Trash/Recycle Bin, broad user caches and additional system scopes remain opt-in.
- The repository version intentionally remains `2.0.2` until this development set is finalized for release.

## 2.0.2 - 2026-08-28

### Fixed

- Fixed `curl .../install.sh | bash` on Termux and other Bash environments where
  `BASH_SOURCE[0]` is unavailable while the installer is read from standard input.
- The Unix installer now validates both local and downloaded `bersihin.py` before installation.
- The installed source is replaced only after the new copy is complete.

### Changed

- Added post-install `bersihin --version` verification.
- Added GitHub Actions smoke tests for clone/local installation and piped Termux-style installation.
- Expanded README and installation documentation to distinguish downloading,
  cloning, and actually executing the installer.

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
