# Updating Bersihin

Current version: `2.0.0`.

## Git clone

```bash
cd bersihin
git pull
```

Re-run the installer if you want to refresh an installed user copy:

```bash
./install.sh
```

or on Windows:

```powershell
.\install.ps1
```

## Built-in update

```bash
bersihin --update
```

The updater:

1. downloads `bersihin.py` from the repository main branch;
2. extracts the remote version;
3. compiles the source in memory to detect syntax errors;
4. creates a `.bak` backup of the currently installed source;
5. atomically replaces the file.

## Maintainer release checklist

For feature additions:

```text
2.0.0 -> 2.1.0
```

For bug fixes:

```text
2.0.0 -> 2.0.1
```

Update at minimum:

```text
bersihin.py (__version__)
VERSION
pyproject.toml
CHANGELOG.md
README.md / README.id.md when behavior changes
```

Create a matching GitHub Release tag such as `v2.1.0`.
