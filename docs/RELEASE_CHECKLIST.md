# Release Checklist

Before publishing a release:

- [ ] Update `__version__`, `VERSION`, and `pyproject.toml`.
- [ ] Move relevant **Unreleased** changelog entries into the release section.
- [ ] `python -m py_compile bersihin.py` passes.
- [ ] `python -m unittest discover -s tests -v` passes.
- [ ] Bash installer syntax and real installer smoke tests pass.
- [ ] PowerShell parser and real Windows installer smoke tests pass.
- [ ] CI passes on Python 3.9, 3.12 and 3.14.
- [ ] Test `--doctor`, `--dry-run`, and real cleanup on affected real platforms.
- [ ] Test same-version/different-source `bersihin --update`.
- [ ] Verify Windows Recycle Bin cleanup is explicitly disclosed before deletion.
- [ ] Confirm no `__pycache__`, `.pyc`, build output, token, password, API key, personal file, or machine-specific secret is committed.
- [ ] Verify quick-install URLs still point to `baska-pro/bersihin`.
- [ ] Create a new immutable tag only after CI and real-platform tests pass.
