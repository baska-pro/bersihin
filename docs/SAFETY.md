# Safety Model

Bersihin v2 is designed around an allowlist instead of "delete everything that looks like cache".

## Default profile

The normal profile targets known user/development caches and age-filtered temporary/log entries.

It avoids:

- filesystem roots;
- the user's home directory itself;
- Windows system roots;
- symlink traversal;
- POSIX temporary entries owned by other users;
- system logs;
- package autoremove;
- Docker prune;
- browser caches unless requested;
- Trash/Recycle Bin unless requested;
- broad generic user caches unless requested.

Project scanning also prunes dependency/build/repository metadata directories where appropriate so the cleaner does not unnecessarily traverse or target unrelated project data.

## Age filtering

The default age threshold is conservative for temporary/log-like targets.

Preview fresh entries with:

```bash
bersihin --older-than 0 --dry-run
```

The scan summary reports how many matched entries were skipped because they were too new.

## `--system`

Includes supported additional system/package caches. Some targets may require Administrator/root privileges.

It does not remove installed packages.

## `--trash`

Includes the user's Trash locations. On Windows, Recycle Bin cleanup uses the shell API rather than manually deleting `$Recycle.Bin`.

## `--browsers`

Targets known browser cache locations only. Close browsers before cleaning to reduce locked-file errors.

## `--aggressive`

Adds broad user-cache roots. Applications may rebuild caches and some sessions can require reauthentication.

Always preview first:

```bash
bersihin --aggressive --dry-run
```

## `--full`

`--full` enables the broader opt-in scopes together:

```text
system + trash + browsers + aggressive
```

It is intended for an explicit broader cleanup, not as the default safety profile.

Recommended:

```bash
bersihin --full --dry-run
```

before:

```bash
bersihin --full
```

## Progress and safety

The realtime progress renderer only changes terminal presentation. It does not expand cleanup scope or bypass confirmation.

`--no-progress` and JSON mode use the same scan/cleanup rules without animation.
