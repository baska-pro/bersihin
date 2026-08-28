## Summary

## Platform(s)

- [ ] Windows
- [ ] Linux
- [ ] Termux
- [ ] WSL
- [ ] macOS/BSD/POSIX

## Safety

- [ ] Dry-run remains non-destructive.
- [ ] No filesystem/home/system root is targeted.
- [ ] Broad/destructive behavior is explicit opt-in.
- [ ] No credentials or private machine data included.

## Validation

- [ ] `python -m unittest discover -s tests -v`
- [ ] `python bersihin.py --doctor`
- [ ] `python bersihin.py --dry-run`
- [ ] Documentation/changelog updated when needed.
