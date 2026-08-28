# Installation

## Requirements

- Python 3.9+
- Windows, Linux, Termux, WSL, macOS, BSD, or another Python-capable POSIX environment

Bersihin has no third-party runtime dependencies.

## Windows

1. Install Python 3.9+ and ensure `py` or `python` is in PATH.
2. Quick install:

```powershell
irm https://raw.githubusercontent.com/baska-pro/bersihin/main/install.ps1 | iex
```

Or clone/download the repository and run:

```powershell
.\install.ps1
```

or `install.cmd`.

The installer copies Bersihin to:

```text
%LOCALAPPDATA%\Bersihin\bersihin.py
```

and creates:

```text
%LOCALAPPDATA%\Programs\Bersihin\bin\bersihin.cmd
```

The bin directory is added to the current user's PATH.

## Linux / WSL / macOS / BSD

Quick install:

```bash
curl -fsSL https://raw.githubusercontent.com/baska-pro/bersihin/main/install.sh | bash
```

Or from a clone:

```bash
./install.sh
```

Default user install:

```text
~/.local/share/bersihin/bersihin.py
~/.local/bin/bersihin
```

If `~/.local/bin` is not in PATH, the installer prints the line to add to your shell profile.

## Termux

```bash
pkg install python git
./install.sh
```

Termux install paths:

```text
$PREFIX/share/bersihin/bersihin.py
$PREFIX/bin/bersihin
```

## Pip / pipx style install

The repository includes `pyproject.toml`, so local package installation is also possible:

```bash
python -m pip install .
```

For isolated CLI installation, `pipx install .` can be used when pipx is available.

## Verify

```bash
bersihin --version
bersihin --doctor
bersihin --dry-run
```
