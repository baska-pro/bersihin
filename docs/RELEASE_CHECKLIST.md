# Release Checklist

Before publishing a release:

- [ ] Update `__version__` in `bersihin.py`.
- [ ] Update `VERSION`.
- [ ] Update version in `pyproject.toml`.
- [ ] Update `CHANGELOG.md`.
- [ ] Update README files if behavior/compatibility changed.
- [ ] `python -m py_compile bersihin.py` passes.
- [ ] `python -m unittest discover -s tests -v` passes.
- [ ] `bash -n install.sh uninstall.sh` passes.
- [ ] Test `--doctor` on affected platforms.
- [ ] Test `--dry-run --verbose` on affected platforms.
- [ ] Confirm dry-run never deletes anything.
- [ ] Review all new cleanup roots for safety.
- [ ] Confirm no token, password, API key, personal file, or machine-specific secret is committed.
- [ ] Verify quick-install URLs point to `baska-pro/bersihin`.
- [ ] Create tag `vX.Y.Z` without rewriting old release tags.
- [ ] Attach tested `bersihin.py`, `install.sh`, and `install.ps1` to GitHub Release.
