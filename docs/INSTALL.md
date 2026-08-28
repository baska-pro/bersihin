# Installation

## Requirements

- Python 3.9+
- Windows, Linux, Termux, WSL, macOS, BSD, or another Python-capable POSIX environment

Bersihin has no third-party Python runtime dependencies.

## Windows

### Quick install

Open PowerShell and run:

```powershell
irm https://raw.githubusercontent.com/baska-pro/bersihin/main/install.ps1 | iex
```

Or clone/download the repository and run:

```powershell
.\install.ps1
```

You can also run `install.cmd`.

The Windows installer copies Bersihin to:

```text
%LOCALAPPDATA%\Bersihin\bersihin.py
```

and creates:

```text
%LOCALAPPDATA%\Programs\Bersihin\bin\bersihin.cmd
```

The bin directory is added to the current user's PATH.

## Linux / WSL / macOS / BSD

### Quick install

This command downloads and executes the installer:

```bash
curl -fsSL https://raw.githubusercontent.com/baska-pro/bersihin/main/install.sh | bash
```

Running the same `curl` command **without** `| bash` only prints the installer; it does not install Bersihin.

### Inspect before running

```bash
curl -fsSL https://raw.githubusercontent.com/baska-pro/bersihin/main/install.sh -o install.sh
less install.sh
bash install.sh
```

### Install from a clone

```bash
git clone https://github.com/baska-pro/bersihin.git
cd bersihin
chmod +x install.sh
./install.sh
```

Default user installation:

```text
~/.local/share/bersihin/bersihin.py
~/.local/bin/bersihin
```

## Termux

Install prerequisites if necessary:

```bash
pkg update
pkg install python curl git
```

Quick install:

```bash
curl -fsSL https://raw.githubusercontent.com/baska-pro/bersihin/main/install.sh | bash
```

Or install from a clone:

```bash
git clone https://github.com/baska-pro/bersihin.git
cd bersihin
chmod +x install.sh
./install.sh
```

Termux installation paths:

```text
$PREFIX/share/bersihin/bersihin.py
$PREFIX/bin/bersihin
```

Refresh shell lookup and verify:

```bash
hash -r 2>/dev/null || true
bersihin --version
bersihin --doctor
bersihin --dry-run --verbose
```

Expected `--doctor` output includes:

```text
Platform family : termux
Detected as     : Termux
Termux          : yes
```

## Pip / pipx style install

```bash
python -m pip install .
```

or, when available:

```bash
pipx install .
```

## Troubleshooting

### `bersihin: command not found`

Cloning the repository does not install the command. Run:

```bash
./install.sh
```

or execute the source directly:

```bash
python bersihin.py --doctor
```

If the installer completed but the shell still cannot find it:

```bash
hash -r 2>/dev/null || true
bersihin --doctor
```

### `BASH_SOURCE[0]: unbound variable`

This piped-installer bug was fixed in Bersihin v2.0.2. Use the current `install.sh` from `main` or the latest release.

## Verify

```bash
bersihin --version
bersihin --doctor
bersihin --dry-run
```
