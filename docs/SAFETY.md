# Safety Model

Bersihin v2 is designed around an allowlist instead of "delete everything that looks like cache".

## Default profile

The normal profile targets known user/development caches and old temporary entries.

It avoids:

- filesystem roots;
- the user's home directory itself;
- Windows system roots;
- symlink traversal;
- POSIX temp entries owned by other users;
- system logs;
- package autoremove;
- Docker prune;
- browser caches unless requested;
- Trash/Recycle Bin unless requested.

## `--system`

Includes supported package download caches and Windows Temp. It may require Administrator/root access.

It does not remove installed packages.

## `--trash`

Empties the user's Trash locations. On Windows it uses the Recycle Bin shell API instead of deleting `$Recycle.Bin` manually.

## `--browsers`

Targets cache subdirectories only. Close browsers before cleaning to reduce locked-file errors.

## `--aggressive`

Adds broad user cache roots such as `~/.cache` or `~/Library/Caches`.

Use a dry run first:

```bash
bersihin --aggressive --dry-run
```

Applications may rebuild caches and some sessions can require reauthentication.

## Dry run first

Recommended before any optional scope:

```bash
bersihin --system --dry-run
bersihin --trash --dry-run
bersihin --browsers --dry-run
bersihin --aggressive --dry-run
```
