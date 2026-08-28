# Security Policy

## Reporting

Do not publish sensitive local paths, credentials, tokens, or private environment information in public Issues.

For a security-sensitive bug, use GitHub private vulnerability reporting when available.

## Cleaner safety

Unexpected deletion outside documented allowlisted cache/temp scopes is considered a security/safety issue.

When reporting, include:

- Bersihin version;
- output of `bersihin --doctor` with private paths redacted if necessary;
- the command used;
- dry-run output;
- operating system/version.

Do not include passwords, API keys, tokens, or personal files.
