# Platform Detection

Bersihin detects the environment at runtime.

Detection priority:

1. Termux (`$PREFIX`, Termux filesystem markers)
2. WSL (Microsoft kernel markers / `WSL_DISTRO_NAME`)
3. native Windows
4. macOS / Darwin
5. Linux
6. BSD
7. generic POSIX/other fallback

`bersihin --doctor` shows the detected platform, architecture, Python interpreter, user, privilege state, important paths and optional tools available in PATH.

## Terminal behavior

Interactive TTY terminals use realtime progress. The layout is automatically shortened on narrow terminals such as Termux on a phone.

Use:

```bash
bersihin --no-progress
```

for static output, or:

```bash
bersihin --force-progress --dry-run
```

when a terminal supports ANSI control sequences but TTY detection is unusual.

JSON output never depends on the terminal progress renderer.

## Project discovery

Bersihin detects likely project roots from common project markers such as `.git`, `pyproject.toml`, `requirements.txt`, `package.json`, `Cargo.toml`, `go.mod`, `composer.json` and build files.

Project scans prune known large/unnecessary subtrees where appropriate rather than traversing every dependency/build directory.

## Unknown environments

On unknown POSIX-like systems the cleaner stays conservative: it uses Python's temporary directory and user-scoped development/cache locations rather than guessing destructive system paths.
