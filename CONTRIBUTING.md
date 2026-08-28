# Contributing

Before submitting a change:

1. Preserve dry-run behavior.
2. Never add a cleanup target that points to a filesystem root, home directory itself, or application data that is not safely reproducible cache/temp data.
3. Make broad/destructive scopes opt-in.
4. Add/update tests when detection or path safety changes.
5. Keep runtime dependencies at zero unless there is a strong reason.
6. Update `CHANGELOG.md` for user-visible changes.
7. Test the affected platform when possible.

Useful bug reports include OS, Python version, `bersihin --doctor`, the exact command, and redacted dry-run output.
