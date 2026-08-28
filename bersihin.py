#!/usr/bin/env python3
"""Bersihin — safe cross-platform development/cache cleaner.

Supported environments are detected automatically: Windows, Linux, Termux,
WSL, macOS, BSD and other POSIX-like systems.
"""
from __future__ import annotations

import argparse
import ctypes
import dataclasses
import datetime as dt
import fnmatch
import getpass
import json
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Iterable, Iterator, Sequence

__version__ = "2.0.1"
APP_NAME = "Bersihin"
REPO = "baska-pro/bersihin"
RAW_SELF_URL = f"https://raw.githubusercontent.com/{REPO}/main/bersihin.py"
RELEASES_URL = f"https://github.com/{REPO}/releases"

# ---------------------------------------------------------------------------
# Terminal output
# ---------------------------------------------------------------------------
USE_COLOR = bool(sys.stdout.isatty() and not os.getenv("NO_COLOR"))


def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if USE_COLOR else text


def info(msg: str) -> None:
    print(f"{_c('1;34', '[*]')} {msg}")


def ok(msg: str) -> None:
    print(f"{_c('1;32', '[+]')} {msg}")


def warn(msg: str) -> None:
    print(f"{_c('1;33', '[!]')} {msg}")


def err(msg: str) -> None:
    print(f"{_c('1;31', '[-]')} {msg}", file=sys.stderr)


def banner() -> None:
    print(_c("1;36", r"""
  ____                 _ _     _       
 | __ )  ___ _ __ ___ (_) |__ (_)_ __  
 |  _ \ / _ \ '__/ __|| | '_ \| | '_ \ 
 | |_) |  __/ |  \__ \| | | | | | | | |
 |____/ \___|_|  |___/|_|_| |_|_|_| |_|
""".rstrip()))
    print(f"Safe cross-platform cleaner v{__version__}\n")


# ---------------------------------------------------------------------------
# Platform detection
# ---------------------------------------------------------------------------
@dataclasses.dataclass(frozen=True)
class Environment:
    family: str
    name: str
    distro: str
    version: str
    is_termux: bool
    is_wsl: bool
    is_windows: bool
    is_macos: bool
    is_linux: bool
    is_bsd: bool
    prefix: str
    home: Path
    temp: Path
    admin: bool


def _os_release() -> dict[str, str]:
    result: dict[str, str] = {}
    path = Path("/etc/os-release")
    if not path.is_file():
        return result
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if "=" not in line or line.startswith("#"):
                continue
            k, v = line.split("=", 1)
            result[k.strip()] = v.strip().strip('"')
    except OSError:
        pass
    return result


def _is_admin_windows() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _is_admin_posix() -> bool:
    return bool(hasattr(os, "geteuid") and os.geteuid() == 0)


def detect_environment() -> Environment:
    system = platform.system().lower()
    home = Path.home()
    prefix = os.environ.get("PREFIX", "")
    is_termux = bool(
        "com.termux" in prefix
        or Path("/data/data/com.termux/files/usr").exists()
        or os.environ.get("TERMUX_VERSION")
    )
    release_text = ""
    for p in (Path("/proc/version"), Path("/proc/sys/kernel/osrelease")):
        try:
            release_text += " " + p.read_text(errors="ignore")
        except OSError:
            pass
    is_wsl = system == "linux" and ("microsoft" in release_text.lower() or bool(os.getenv("WSL_DISTRO_NAME")))
    is_windows = os.name == "nt" or system == "windows"
    is_macos = system == "darwin"
    is_linux = system == "linux" and not is_termux
    is_bsd = system in {"freebsd", "openbsd", "netbsd", "dragonfly"}
    osr = _os_release()

    if is_termux:
        family, name = "termux", "Termux"
        distro = "Android/Termux"
    elif is_wsl:
        family, name = "wsl", "Windows Subsystem for Linux"
        distro = osr.get("PRETTY_NAME") or osr.get("NAME") or "WSL Linux"
    elif is_windows:
        family, name = "windows", "Windows"
        distro = platform.platform()
    elif is_macos:
        family, name = "macos", "macOS"
        distro = f"macOS {platform.mac_ver()[0]}".strip()
    elif is_linux:
        family, name = "linux", "Linux"
        distro = osr.get("PRETTY_NAME") or osr.get("NAME") or platform.platform()
    elif is_bsd:
        family, name = "bsd", platform.system()
        distro = platform.platform()
    else:
        family, name = "posix" if os.name == "posix" else "other", platform.system() or os.name
        distro = platform.platform()

    return Environment(
        family=family,
        name=name,
        distro=distro,
        version=platform.version(),
        is_termux=is_termux,
        is_wsl=is_wsl,
        is_windows=is_windows,
        is_macos=is_macos,
        is_linux=is_linux,
        is_bsd=is_bsd,
        prefix=prefix,
        home=home,
        temp=Path(tempfile.gettempdir()),
        admin=_is_admin_windows() if is_windows else _is_admin_posix(),
    )


# ---------------------------------------------------------------------------
# Safe filesystem planner
# ---------------------------------------------------------------------------
@dataclasses.dataclass(frozen=True)
class Rule:
    label: str
    category: str
    root: Path
    patterns: tuple[str, ...] = ("*",)
    min_age_days: int = 0
    recursive: bool = True
    owner_only: bool = False
    note: str = ""


@dataclasses.dataclass
class Candidate:
    path: Path
    label: str
    category: str
    size: int
    mtime: float


@dataclasses.dataclass
class Result:
    scanned_bytes: int = 0
    removed_bytes: int = 0
    candidates: int = 0
    removed: int = 0
    skipped: int = 0
    errors: int = 0


PROTECTED_NAMES = {"windows", "system32", "program files", "program files (x86)"}


def human_bytes(n: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(max(0, n))
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.2f} {unit}"
        value /= 1024
    return f"{n} B"


def path_size(path: Path) -> int:
    try:
        if path.is_symlink():
            return 0
        if path.is_file():
            return path.stat().st_size
        total = 0
        for base, dirs, files in os.walk(path, topdown=True, followlinks=False):
            dirs[:] = [d for d in dirs if not (Path(base) / d).is_symlink()]
            for name in files:
                p = Path(base) / name
                try:
                    if not p.is_symlink():
                        total += p.stat().st_size
                except OSError:
                    pass
        return total
    except OSError:
        return 0


def _same_owner(path: Path) -> bool:
    if os.name == "nt" or not hasattr(os, "geteuid"):
        return True
    try:
        return os.stat(path, follow_symlinks=False).st_uid == os.geteuid()
    except OSError:
        return False


def _is_dangerous_target(path: Path, env: Environment) -> bool:
    try:
        p = path.expanduser().absolute()
    except OSError:
        return True
    text = str(p).rstrip("/\\")
    if not text:
        return True
    protected = {Path("/"), env.home.absolute()}
    if env.is_windows:
        for key in ("SystemRoot", "WINDIR", "ProgramFiles", "ProgramFiles(x86)"):
            val = os.getenv(key)
            if val:
                protected.add(Path(val).absolute())
        drive = p.drive
        if drive:
            protected.add(Path(drive + "\\"))
    if p in protected:
        return True
    if p.name.lower() in PROTECTED_NAMES and p.parent == Path(p.anchor):
        return True
    return False


def _iter_direct_children(root: Path) -> Iterator[Path]:
    try:
        for child in root.iterdir():
            yield child
    except (OSError, PermissionError):
        return


def _matches(path: Path, patterns: Sequence[str]) -> bool:
    return any(fnmatch.fnmatch(path.name, pat) for pat in patterns)


def _old_enough(path: Path, age_days: int, now: float) -> bool:
    if age_days <= 0:
        return True
    try:
        return now - os.stat(path, follow_symlinks=False).st_mtime >= age_days * 86400
    except OSError:
        return False


def expand_rule(rule: Rule, env: Environment) -> Iterator[Candidate]:
    root = rule.root.expanduser()
    if not root.exists() or root.is_symlink() or _is_dangerous_target(root, env):
        return
    now = time.time()
    iterator: Iterable[Path]
    if rule.recursive and rule.patterns != ("*",):
        def walk() -> Iterator[Path]:
            for base, dirs, files in os.walk(root, topdown=True, followlinks=False):
                dirs[:] = [d for d in dirs if not (Path(base) / d).is_symlink()]
                for name in files:
                    yield Path(base) / name
                for name in dirs:
                    yield Path(base) / name
        iterator = walk()
    else:
        iterator = _iter_direct_children(root)

    seen: set[str] = set()
    for p in iterator:
        try:
            if p.is_symlink():
                continue
            if not _matches(p, rule.patterns):
                continue
            if rule.owner_only and not _same_owner(p):
                continue
            if not _old_enough(p, rule.min_age_days, now):
                continue
            key = os.path.normcase(str(p.absolute()))
            if key in seen or _is_dangerous_target(p, env):
                continue
            seen.add(key)
            yield Candidate(p, rule.label, rule.category, path_size(p), p.stat().st_mtime)
        except (OSError, PermissionError):
            continue


def _add_existing_rule(rules: list[Rule], label: str, category: str, path: Path | str | None,
                       *, age: int = 0, patterns: tuple[str, ...] = ("*",),
                       recursive: bool = True, owner_only: bool = False, note: str = "") -> None:
    if not path:
        return
    p = Path(path).expanduser()
    rules.append(Rule(label, category, p, patterns, age, recursive, owner_only, note))


def _command_output(args: Sequence[str]) -> str:
    try:
        cp = subprocess.run(args, capture_output=True, text=True, timeout=8,
                            encoding="utf-8", errors="replace")
        return cp.stdout.strip() if cp.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def build_rules(env: Environment, args: argparse.Namespace) -> list[Rule]:
    rules: list[Rule] = []
    home = env.home
    age = max(0, args.older_than)
    xdg_cache = Path(os.getenv("XDG_CACHE_HOME") or (home / ".cache"))

    # User/OS temporary files: only old children, never delete the temp root itself.
    # When running as POSIX root, shared /tmp often contains root-owned service files;
    # skip that broad root by default rather than treating root ownership as user ownership.
    shared_posix_temp_as_root = (
        os.name == "posix" and env.admin and not env.is_termux
        and env.temp in {Path("/tmp"), Path("/var/tmp")}
    )
    if not shared_posix_temp_as_root:
        _add_existing_rule(rules, "Temporary files", "temp", env.temp,
                           age=age, owner_only=not env.is_windows)
    if env.is_termux and env.prefix:
        _add_existing_rule(rules, "Termux tmp", "temp", Path(env.prefix) / "tmp", age=age)

    # Python/pip.
    if env.is_windows:
        local = os.getenv("LOCALAPPDATA")
        _add_existing_rule(rules, "pip cache", "dev", Path(local) / "pip" / "Cache" if local else None)
    elif env.is_macos:
        _add_existing_rule(rules, "pip cache", "dev", home / "Library" / "Caches" / "pip")
    else:
        _add_existing_rule(rules, "pip cache", "dev", xdg_cache / "pip")

    # Python bytecode only under selected user project roots, never the whole filesystem.
    for project_root in [home / "projects", home / "src", home / "apps", Path.cwd()]:
        if (project_root.exists() and project_root != home
                and not _is_dangerous_target(project_root, env)):
            _add_existing_rule(rules, "Python __pycache__", "dev", project_root,
                               patterns=("__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"),
                               recursive=True, owner_only=True)

    # Node / package manager caches.
    npm_cache = _command_output(["npm", "config", "get", "cache"]) if shutil.which("npm") else ""
    if npm_cache and npm_cache.lower() not in {"undefined", "null"}:
        _add_existing_rule(rules, "npm cache", "dev", Path(npm_cache) / "_cacache")
    else:
        _add_existing_rule(rules, "npm cache", "dev", home / ".npm" / "_cacache")

    yarn_cache = _command_output(["yarn", "cache", "dir"]) if shutil.which("yarn") else ""
    if yarn_cache:
        _add_existing_rule(rules, "Yarn cache", "dev", yarn_cache)
    else:
        _add_existing_rule(rules, "Yarn cache", "dev", xdg_cache / "yarn")
    _add_existing_rule(rules, "pnpm cache", "dev", xdg_cache / "pnpm")
    if env.is_windows:
        local = os.getenv("LOCALAPPDATA")
        if local:
            if not yarn_cache:
                _add_existing_rule(rules, "Yarn cache", "dev", Path(local) / "Yarn" / "Cache")
            _add_existing_rule(rules, "pnpm store metadata", "dev", Path(local) / "pnpm-cache")
            _add_existing_rule(rules, "NuGet HTTP cache", "dev", Path(local) / "NuGet" / "v3-cache")
        _add_existing_rule(rules, "Scoop download cache", "packages", home / "scoop" / "cache")
    if env.is_macos:
        _add_existing_rule(rules, "Homebrew download cache", "packages", home / "Library" / "Caches" / "Homebrew")

    # Go build cache: queried from the installed Go tool when available.
    if shutil.which("go"):
        gocache = _command_output(["go", "env", "GOCACHE"])
        if gocache and gocache.lower() != "off":
            _add_existing_rule(rules, "Go build cache", "dev", gocache)

    # Rust download archives only. Keep installed binaries and registry index/source.
    _add_existing_rule(rules, "Cargo registry download cache", "dev", home / ".cargo" / "registry" / "cache")

    # Composer cache location when Composer is installed.
    if shutil.which("composer"):
        comp = _command_output(["composer", "config", "cache-dir", "--global"])
        if comp:
            _add_existing_rule(rules, "Composer cache", "dev", comp)

    # Gradle build cache only, not downloaded dependency modules.
    gradle = home / ".gradle" / "caches"
    if gradle.exists():
        for p in gradle.glob("build-cache-*"):
            _add_existing_rule(rules, "Gradle build cache", "dev", p)

    # Package manager download caches. System-owned caches are opt-in.
    if env.is_termux and env.prefix:
        _add_existing_rule(rules, "Termux APT archives", "packages", Path(env.prefix) / "var/cache/apt/archives",
                           patterns=("*.deb",), recursive=False)
    if args.system:
        if env.family in {"linux", "wsl"}:
            _add_existing_rule(rules, "APT package archives", "system", "/var/cache/apt/archives",
                               patterns=("*.deb",), recursive=False)
            _add_existing_rule(rules, "DNF cache", "system", "/var/cache/dnf")
            _add_existing_rule(rules, "APK cache", "system", "/var/cache/apk")
        if env.is_windows:
            windir = os.getenv("WINDIR") or r"C:\Windows"
            _add_existing_rule(rules, "Windows Temp", "system", Path(windir) / "Temp",
                               age=age, owner_only=not env.admin)

    # Trash/recycle bin is explicit because users may expect recovery.
    if args.trash:
        if env.is_windows:
            # Windows recycle bin is handled by shell API separately; no raw path deletion here.
            pass
        elif env.is_macos:
            _add_existing_rule(rules, "Trash", "trash", home / ".Trash")
        else:
            _add_existing_rule(rules, "Trash files", "trash", home / ".local/share/Trash/files")
            _add_existing_rule(rules, "Trash metadata", "trash", home / ".local/share/Trash/info")

    # Browser caches are explicit; browser profiles/settings are not targeted.
    if args.browsers:
        if env.is_windows:
            local = os.getenv("LOCALAPPDATA")
            roaming = os.getenv("APPDATA")
            if local:
                for base in [Path(local)/"Google/Chrome/User Data", Path(local)/"Microsoft/Edge/User Data",
                             Path(local)/"Chromium/User Data"]:
                    if base.exists():
                        for profile in base.glob("*"):
                            for sub in ("Cache", "Code Cache", "GPUCache"):
                                _add_existing_rule(rules, f"Browser {sub}", "browsers", profile/sub)
            # Firefox keeps profile configuration under APPDATA but caches under LOCALAPPDATA.
            for ffroot in [
                Path(local) / "Mozilla/Firefox/Profiles" if local else None,
                Path(roaming) / "Mozilla/Firefox/Profiles" if roaming else None,
            ]:
                if ffroot and ffroot.exists():
                    for profile in ffroot.glob("*"):
                        _add_existing_rule(rules, "Firefox cache", "browsers", profile/"cache2")
        elif env.is_macos:
            for p in [home/"Library/Caches/Google/Chrome", home/"Library/Caches/Microsoft Edge",
                      home/"Library/Caches/Firefox"]:
                _add_existing_rule(rules, "Browser cache", "browsers", p)
        else:
            for p in [home/".cache/google-chrome", home/".cache/chromium", home/".cache/microsoft-edge",
                      home/".cache/mozilla/firefox"]:
                _add_existing_rule(rules, "Browser cache", "browsers", p)

    # Aggressive generic user cache is never part of the default profile.
    if args.aggressive:
        if env.is_windows:
            local = os.getenv("LOCALAPPDATA")
            if local:
                _add_existing_rule(rules, "Generic user cache", "aggressive", Path(local) / "Temp", age=age)
        elif env.is_macos:
            _add_existing_rule(rules, "Generic user cache", "aggressive", home / "Library/Caches", age=age)
        else:
            _add_existing_rule(rules, "Generic user cache", "aggressive", xdg_cache, age=age)

    return rules


def collect_candidates(rules: Sequence[Rule], env: Environment, categories: set[str] | None = None) -> list[Candidate]:
    candidates: list[Candidate] = []
    seen: set[str] = set()
    for rule in rules:
        if categories and rule.category not in categories:
            continue
        for cand in expand_rule(rule, env):
            key = os.path.normcase(str(cand.path.absolute()))
            # If a parent was already selected, do not double count its descendants.
            if any(key.startswith(parent + os.sep) for parent in seen):
                continue
            # Remove descendants already added if their parent arrives later.
            survivors: list[Candidate] = []
            for old in candidates:
                oldkey = os.path.normcase(str(old.path.absolute()))
                if oldkey.startswith(key + os.sep):
                    seen.discard(oldkey)
                else:
                    survivors.append(old)
            candidates = survivors
            seen.add(key)
            candidates.append(cand)
    return candidates


def delete_candidate(cand: Candidate) -> tuple[bool, str]:
    p = cand.path
    try:
        if p.is_symlink():
            return False, "symlink skipped"
        if p.is_dir():
            shutil.rmtree(p)
        else:
            # Clear readonly flag where possible.
            try:
                p.chmod(stat.S_IWRITE | stat.S_IREAD)
            except OSError:
                pass
            p.unlink()
        return True, ""
    except (OSError, PermissionError) as exc:
        return False, str(exc)


def empty_windows_recycle_bin(*, dry_run: bool) -> tuple[bool, str]:
    if os.name != "nt":
        return False, "not Windows"
    if dry_run:
        return True, "Recycle Bin would be emptied"
    try:
        # SHERB_NOCONFIRMATION | SHERB_NOPROGRESSUI | SHERB_NOSOUND
        flags = 0x1 | 0x2 | 0x4
        rc = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, flags)
        return rc == 0, "" if rc == 0 else f"Shell return code {rc}"
    except Exception as exc:
        return False, str(exc)


# ---------------------------------------------------------------------------
# Update / uninstall helpers
# ---------------------------------------------------------------------------
def _extract_remote_version(source: str) -> str:
    m = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']', source, re.M)
    return m.group(1) if m else "unknown"


def self_update() -> int:
    info(f"Checking {RAW_SELF_URL}")
    try:
        req = urllib.request.Request(RAW_SELF_URL, headers={"User-Agent": f"bersihin/{__version__}"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            source = resp.read().decode("utf-8")
    except (urllib.error.URLError, OSError, UnicodeError) as exc:
        err(f"Update failed: {exc}")
        return 1

    remote_version = _extract_remote_version(source)
    if remote_version == "unknown":
        err("Downloaded file does not look like a valid Bersihin source.")
        return 1
    try:
        compile(source, "<bersihin-update>", "exec")
    except SyntaxError as exc:
        err(f"Downloaded update failed syntax validation: {exc}")
        return 1

    current = Path(__file__).resolve()
    if any(part.lower() in {"site-packages", "dist-packages"} for part in current.parts):
        err("This copy is installed as a Python package. Update the source/package installation instead of self-replacing site-packages.")
        return 1
    if remote_version == __version__:
        ok(f"Already on the latest published source ({__version__}).")
        return 0

    backup = current.with_suffix(current.suffix + ".bak")
    tmp = current.with_suffix(current.suffix + ".tmp")
    try:
        shutil.copy2(current, backup)
        tmp.write_text(source, encoding="utf-8", newline="\n")
        os.replace(tmp, current)
        try:
            current.chmod(current.stat().st_mode | stat.S_IXUSR)
        except OSError:
            pass
        ok(f"Updated {__version__} -> {remote_version}")
        info(f"Backup: {backup}")
        return 0
    except OSError as exc:
        err(f"Cannot replace {current}: {exc}")
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        return 1


def uninstall_self(yes: bool) -> int:
    current = Path(__file__).resolve()
    home = Path.home()
    targets = [
        current,
        home / ".local/bin/bersihin",
        home / ".local/share/bersihin/bersihin.py",
    ]
    if os.name == "nt":
        local = os.getenv("LOCALAPPDATA")
        if local:
            targets += [
                Path(local) / "Bersihin/bersihin.py",
                Path(local) / "Programs/Bersihin/bin/bersihin.cmd",
            ]
    prefix = os.getenv("PREFIX")
    if prefix:
        targets += [Path(prefix)/"bin/bersihin", Path(prefix)/"share/bersihin/bersihin.py"]

    if not yes:
        ans = input("Remove Bersihin from this user account? [y/N]: ").strip().lower()
        if ans not in {"y", "yes"}:
            info("Uninstall cancelled.")
            return 0
    failures = 0
    for p in dict.fromkeys(targets):
        try:
            if p.is_symlink() or p.is_file():
                p.unlink()
                ok(f"Removed {p}")
        except OSError as exc:
            failures += 1
            warn(f"Could not remove {p}: {exc}")
    return 1 if failures else 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="bersihin",
        description="Safe cross-platform cleaner for Windows, Linux, Termux, WSL, macOS and POSIX systems.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--dry-run", "--scan", action="store_true", dest="dry_run",
                   help="Scan and show reclaimable data without deleting anything")
    p.add_argument("--yes", "-y", action="store_true", help="Do not ask for confirmation")
    p.add_argument("--older-than", type=int, default=2,
                   help="Minimum age in days for temporary/generic cache entries")
    p.add_argument("--category", action="append", choices=["temp", "dev", "packages", "system", "trash", "browsers", "aggressive"],
                   help="Only process selected category; may be repeated")
    p.add_argument("--system", action="store_true", help="Include supported system/package caches; may require admin/root")
    p.add_argument("--trash", action="store_true", help="Include user Trash / Recycle Bin")
    p.add_argument("--browsers", action="store_true", help="Include browser cache directories; close browsers first")
    p.add_argument("--aggressive", action="store_true", help="Include broad user cache directories (not recommended for routine use)")
    p.add_argument("--json", action="store_true", help="Print scan/result data as JSON")
    p.add_argument("--verbose", "-v", action="store_true", help="List every measured candidate path")
    p.add_argument("--list-targets", action="store_true", help="Show cleanup rules/roots selected for this platform")
    p.add_argument("--doctor", action="store_true", help="Show detected platform, tools, paths and privilege state")
    p.add_argument("--update", action="store_true", help="Update this installed script from GitHub main")
    p.add_argument("--uninstall", action="store_true", help="Remove installed Bersihin files for the current user")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def doctor(env: Environment) -> int:
    banner()
    print(f"Platform family : {env.family}")
    print(f"Detected as     : {env.name}")
    print(f"Distribution    : {env.distro}")
    print(f"Architecture    : {platform.machine()}")
    print(f"Python          : {platform.python_version()} ({sys.executable})")
    print(f"User            : {getpass.getuser()}")
    print(f"Admin/root      : {'yes' if env.admin else 'no'}")
    print(f"Home            : {env.home}")
    print(f"Temp            : {env.temp}")
    print(f"PREFIX          : {env.prefix or '-'}")
    print(f"WSL             : {'yes' if env.is_wsl else 'no'}")
    print(f"Termux          : {'yes' if env.is_termux else 'no'}")
    print("Tools           :")
    for name in ["git", "curl", "pip", "pip3", "npm", "yarn", "pnpm", "go", "cargo", "composer", "docker"]:
        print(f"  {name:<10} {shutil.which(name) or '-'}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    env = detect_environment()

    if args.update:
        return self_update()
    if args.uninstall:
        return uninstall_self(args.yes)
    if args.doctor:
        return doctor(env)
    selected_categories = set(args.category or [])
    # Category selection should be intuitive: selecting an opt-in category enables
    # its corresponding rule group automatically.
    if "system" in selected_categories:
        args.system = True
    if "trash" in selected_categories:
        args.trash = True
    if "browsers" in selected_categories:
        args.browsers = True
    if "aggressive" in selected_categories:
        args.aggressive = True
    if args.older_than < 0:
        err("--older-than cannot be negative")
        return 2

    rules = build_rules(env, args)
    if args.list_targets:
        banner()
        info(f"Detected: {env.name} | {env.distro}")
        for rule in rules:
            print(f"{rule.category:<11} {rule.label:<34} {rule.root}")
        return 0
    categories = selected_categories or None
    candidates = collect_candidates(rules, env, categories)
    result = Result(
        scanned_bytes=sum(c.size for c in candidates),
        candidates=len(candidates),
    )

    if args.json:
        payload = {
            "app": APP_NAME,
            "version": __version__,
            "environment": dataclasses.asdict(env),
            "dry_run": args.dry_run,
            "options": {
                "system": args.system,
                "trash": args.trash,
                "browsers": args.browsers,
                "aggressive": args.aggressive,
                "older_than": args.older_than,
                "categories": sorted(categories) if categories else None,
            },
            "candidates": [
                {"path": str(c.path), "label": c.label, "category": c.category, "size": c.size}
                for c in candidates
            ],
            "reclaimable_bytes": result.scanned_bytes,
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
        return 0 if args.dry_run else 0

    banner()
    info(f"Detected: {env.name} | {env.distro}")
    info(f"Profile: safe default{' + system' if args.system else ''}{' + trash' if args.trash else ''}{' + browsers' if args.browsers else ''}{' + aggressive' if args.aggressive else ''}")

    if not candidates and not (args.trash and env.is_windows):
        ok("Nothing eligible to clean.")
        return 0

    grouped: dict[str, tuple[int, int]] = {}
    for c in candidates:
        count, size = grouped.get(c.label, (0, 0))
        grouped[c.label] = (count + 1, size + c.size)
    print("\nScan result:")
    for label, (count, size) in sorted(grouped.items(), key=lambda kv: kv[1][1], reverse=True):
        print(f"  {label:<34} {count:>5} item(s)  {human_bytes(size):>12}")
    if args.trash and env.is_windows:
        print(f"  {'Windows Recycle Bin':<34} {'?':>5} item(s)  {'unknown':>12}")
    print(f"  {'TOTAL':<34} {len(candidates):>5} item(s)  {human_bytes(result.scanned_bytes):>12}\n")
    if args.verbose:
        print("Candidates:")
        for cand in sorted(candidates, key=lambda c: str(c.path).lower()):
            print(f"  [{cand.category:<10}] {human_bytes(cand.size):>10}  {cand.path}")
        print()

    if args.dry_run:
        ok(f"Dry-run complete. Reclaimable from measured targets: {human_bytes(result.scanned_bytes)}")
        return 0

    if args.aggressive:
        warn("Aggressive mode includes broad user caches. Applications may rebuild caches or sign you out of some sessions.")
    if args.browsers:
        warn("Close browsers before cleaning browser caches to reduce locked-file errors.")
    if args.system and not env.admin:
        warn("System cache cleanup may be incomplete without Administrator/root privileges.")

    if not args.yes:
        ans = input(f"Clean {len(candidates)} measured item(s) ({human_bytes(result.scanned_bytes)})? [y/N]: ").strip().lower()
        if ans not in {"y", "yes"}:
            info("Cancelled; nothing was deleted.")
            return 0

    started = time.time()
    for cand in candidates:
        success, detail = delete_candidate(cand)
        if success:
            result.removed += 1
            result.removed_bytes += cand.size
        else:
            result.errors += 1
            if detail:
                warn(f"Skipped {cand.path}: {detail}")

    if args.trash and env.is_windows:
        success, detail = empty_windows_recycle_bin(dry_run=False)
        if not success:
            result.errors += 1
            warn(f"Recycle Bin: {detail}")
        else:
            ok("Windows Recycle Bin emptied.")

    elapsed = time.time() - started
    print()
    ok(f"Finished in {elapsed:.1f}s. Removed {result.removed} measured item(s), about {human_bytes(result.removed_bytes)}.")
    if result.errors:
        warn(f"{result.errors} item/action(s) could not be completed.")
    print(f"Time: {dt.datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')}")
    return 0 if not result.errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
