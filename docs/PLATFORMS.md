# Platform Detection

Bersihin detects the environment at runtime.

Priority:

1. Termux (`$PREFIX`, Termux filesystem markers)
2. WSL (Microsoft kernel markers / `WSL_DISTRO_NAME`)
3. Native Windows
4. macOS / Darwin
5. Linux
6. BSD
7. generic POSIX/other fallback

`bersihin --doctor` shows the exact result, Python interpreter, user, privilege state, important paths, and optional tools detected in PATH.

The cleaner is conservative on unknown environments: it uses Python's temporary directory and user-scoped development caches rather than guessing system-specific cache locations.
