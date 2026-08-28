# Installation

## Requirements

- Python 3.9+
- Windows, Linux, Termux, WSL, macOS, BSD, or another Python-capable POSIX environment

Bersihin has no third-party Python runtime dependencies.

## Windows

Quick install:

```powershell
irm https://raw.githubusercontent.com/baska-pro/bersihin/main/install.ps1 | iex
```

Piped mode always downloads the current GitHub source unless the maintainer-only `BERSIHIN_SOURCE` override is explicitly supplied. A random `bersihin.py` in the current directory is not trusted. Python 3.9+ and the source syntax are validated before installation.

From a clone:

```powershell
git clone https://github.com/baska-pro/bersihin.git
cd bersihin
.\install.ps1
```

A file-based local installer may use `bersihin.py` beside `install.ps1`, after validation.

Installed paths:

```text
%LOCALAPPDATA%\Bersihin\bersihin.py
%LOCALAPPDATA%\Programs\Bersihin\bin\bersihin.cmd
```

## Linux / WSL / macOS / BSD / Termux

Quick install:

```bash
curl -fsSL https://raw.githubusercontent.com/baska-pro/bersihin/main/install.sh | bash
```

`curl` without `| bash` only prints the installer.

From a clone:

```bash
git clone https://github.com/baska-pro/bersihin.git
cd bersihin
chmod +x install.sh
./install.sh
```

Termux prerequisites when needed:

```bash
pkg update
pkg install python curl git
```

Verify:

```bash
hash -r 2>/dev/null || true
bersihin --version
bersihin --doctor
bersihin --dry-run
```

`BERSIHIN_SOURCE=/path/to/bersihin.py` is supported for maintainer CI/offline verification. Normal users do not need it.
