# Migrating from Bersihin v1

Bersihin v1 was Bash-first and primarily targeted Termux/Linux. Version 2 uses a Python standard-library core to support Windows and additional platforms safely.

## Existing Linux / Termux install

Run the v2 installer. It will replace the `bersihin` command symlink with the v2 executable while leaving the old `~/.bersihin` directory untouched for safety.

After verifying:

```bash
bersihin --version
bersihin --doctor
bersihin --dry-run
```

you may remove the old v1 directory manually if it is no longer needed:

```bash
rm -rf ~/.bersihin
```

Only do this if that directory is the old Bersihin installation and does not contain your own unrelated files.

## Behavior changes

Version 2 no longer performs several broad cleanup actions by default:

- no automatic `apt autoremove`;
- no blanket system-log truncation;
- no blanket `/tmp` wipe;
- no blanket `~/.cache` wipe;
- no browser/trash cleanup unless explicitly requested.

Use `--list-targets` and `--dry-run --verbose` to inspect the new plan.
