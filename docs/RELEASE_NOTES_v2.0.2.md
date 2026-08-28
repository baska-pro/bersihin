# Bersihin v2.0.2

Maintenance release focused on public installation reliability and documentation.

## Fixed

- Fixed Unix/Termux quick installation with:

```bash
curl -fsSL https://raw.githubusercontent.com/baska-pro/bersihin/main/install.sh | bash
```

- Fixed `BASH_SOURCE[0]: unbound variable` when Bash reads `install.sh` from standard input.
- The installer validates `bersihin.py` before replacing an existing installation.
- Installation uses a temporary destination file before activating the new source.

## Installer verification

CI now tests both documented Unix installation flows:

```bash
./install.sh
```

and piped installation equivalent to:

```bash
curl -fsSL https://raw.githubusercontent.com/baska-pro/bersihin/main/install.sh | bash
```

Termux-style installation is smoke-tested using a simulated `$PREFIX`.

## Documentation

README, README Indonesia, and `docs/INSTALL.md` now explain that running `curl` without `| bash` only displays the script and does not install Bersihin.

## Upgrade

For a Git clone:

```bash
git pull
./install.sh
```

For an installed standalone source:

```bash
bersihin --update
```

Then verify:

```bash
bersihin --version
bersihin --doctor
bersihin --dry-run --verbose
```

Expected version:

```text
2.0.2
```

## Requirements

- Python 3.9+
- Windows, Linux, Termux, WSL, macOS, BSD, or another supported Python-capable environment
