# Updating Bersihin

Current development version: `2.0.2`.

The `main` branch may contain **Unreleased** source changes while the visible version remains `2.0.2`.

## Git clone

```bash
cd bersihin
git pull
./install.sh
```

Windows:

```powershell
git pull
.\install.ps1
```

## Built-in update

```bash
bersihin --update
```

The updater downloads `main`, validates it, compares both the version and SHA-256 source fingerprint, creates a `.bak`, validates the temporary replacement, and atomically activates the new source.

If local and remote both report `2.0.2` but their source hashes differ, the source is refreshed instead of incorrectly reporting that it is already current. This behavior is useful while Unreleased work remains on `main`.

Package-managed installs inside `site-packages` / `dist-packages` must be updated using the package/source installation method instead.

The version should only be bumped when the next release is finalized.
