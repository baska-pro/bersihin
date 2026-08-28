#!/usr/bin/env python3
"""Bersihin - safe, informative, cross-platform cache/temp cleaner.

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
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable, Iterable, Iterator, Sequence

__version__ = "2.0.2"
APP_NAME = "Bersihin"
REPO = "baska-pro/bersihin"
RAW_SELF_URL = f"https://raw.githubusercontent.com/{REPO}/main/bersihin.py"
RELEASES_URL = f"https://github.com/{REPO}/releases"

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
# Realtime terminal progress / responsive output
# ---------------------------------------------------------------------------
MIN_SCAN_ANIMATION_SECONDS = 1.15
MIN_CLEAN_ANIMATION_SECONDS = 0.90
PROGRESS_FRAME_INTERVAL = 0.11
PROGRESS_MAX_STEP_PERCENT = 9.0


def _terminal_width(default: int = 100) -> int:
    """Return the real terminal width without pretending a phone terminal is wide."""
    try:
        return max(32, min(180, shutil.get_terminal_size((default, 24)).columns))
    except OSError:
        return default


def _compact_terminal() -> bool:
    return _terminal_width() < 78


def _shorten_right(value: str, max_len: int) -> str:
    value = str(value)
    if max_len <= 0:
        return ""
    if len(value) <= max_len:
        return value
    if max_len <= 3:
        return value[:max_len]
    return value[: max_len - 3] + "..."


def _shorten_middle(value: str, max_len: int) -> str:
    value = str(value)
    if max_len <= 0:
        return ""
    if len(value) <= max_len:
        return value
    if max_len <= 3:
        return value[:max_len]
    remaining = max_len - 3
    left = max(1, remaining // 2)
    right = max(1, remaining - left)
    return value[:left] + "..." + value[-right:]


def _pack_detail_lines(tokens: Sequence[str], width: int, indent: str = "     ") -> list[str]:
    """Pack detail tokens across lines without chopping values such as durations."""
    usable = max(12, width - len(indent) - 1)
    lines: list[str] = []
    current = ""
    for token in [str(t) for t in tokens if str(t)]:
        token = _shorten_right(token, usable)
        proposed = token if not current else current + " | " + token
        if current and len(proposed) > usable:
            lines.append(indent + current)
            current = token
        else:
            current = proposed
    if current:
        lines.append(indent + current)
    return lines or [indent.rstrip()]


def _progress_bar(done: float, total: float, width: int | None = None,
                  *, pulse: int | None = None) -> str:
    """Readable ASCII progress bar with a slow moving head.

    `done` may be fractional. The bar intentionally avoids a fast spinner; on
    short Termux scans the user sees the bar fill smoothly instead.
    """
    if width is None:
        width = 16 if _compact_terminal() else 24
    width = max(8, int(width))
    ratio = 0.0 if total <= 0 else max(0.0, min(1.0, float(done) / float(total)))
    filled = int(ratio * width)

    chars = ["=" if i < filled else " " for i in range(width)]
    if ratio < 1.0:
        head = min(filled, width - 1)
        chars[head] = ">"
        # A very slow pulse behind the head provides motion without the noisy
        # | / - \ spinner. One pulse step is ~2 frames.
        if pulse is not None and filled > 1:
            tail = max(0, head - 1 - ((pulse // 2) % min(3, filled)))
            if tail < head:
                chars[tail] = "-"
    return "[" + "".join(chars) + "]"


def human_duration(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    if seconds < 0.001:
        return "<1 ms"
    if seconds < 1.0:
        return f"{seconds * 1000:.0f} ms"
    if seconds < 60.0:
        return f"{seconds:.2f}s"
    minutes, sec = divmod(int(round(seconds)), 60)
    if minutes < 60:
        return f"{minutes}m {sec:02d}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes:02d}m {sec:02d}s"


def _friendly_label(label: str) -> str:
    """Make repeated per-project rule names easier to scan on narrow terminals."""
    patterns = (
        (r"^Python project cache \((.+)\)$", "Project {0} - Python"),
        (r"^Node project cache \((.+)\)$", "Project {0} - Node"),
        (r"^JS build cache \((.+)\)$", "Project {0} - JS build"),
    )
    for pattern, template in patterns:
        m = re.match(pattern, label)
        if m:
            return template.format(m.group(1))
    return label


def _live_progress_text(action: str, done: int, total: int, label: str,
                        *, checked: int = 0, eligible: int = 0,
                        matched: int = 0, elapsed: float = 0.0,
                        frame: int = 0, current: Path | None = None,
                        visual_pct: float | None = None) -> str:
    actual_pct = (done / total * 100.0) if total else 100.0
    pct_value = actual_pct if visual_pct is None else max(0.0, min(100.0, visual_pct))
    pct = int(round(pct_value))
    label = _friendly_label(label)
    width = _terminal_width()
    bar = _progress_bar(pct_value, 100.0, pulse=frame)

    if width < 78:
        # Termux/phone: show the progress bar first and preserve the useful
        # counters. Current path is intentionally omitted to avoid wrapping.
        base = f"{bar} {pct:3d}% "
        counters = f" | {done}/{total} | chk {checked:,}"
        if matched:
            counters += f" m {matched:,}"
        if eligible:
            counters += f" f {eligible:,}"
        counters += f" | {human_duration(elapsed)}"
        label_width = max(8, width - len(base) - len(counters) - 1)
        return base + _shorten_right(label, label_width) + counters

    current_text = ""
    if current is not None:
        current_text = f" | {_shorten_middle(str(current), 28)}"
    return (
        f"{bar} {pct:3d}% | {done}/{total} | {_shorten_right(label, 30)} | "
        f"checked {checked:,} | matched {matched:,} | eligible {eligible:,} | "
        f"{human_duration(elapsed)}{current_text}"
    )


def _final_scan_lines(idx: int, total: int, row: "RuleScan", elapsed: float) -> list[str]:
    label = _friendly_label(row.label)
    status = row.status
    if status == "FOUND":
        marker = "DATA"
        tokens = [
            f"checked {row.checked:,}",
            f"matched {row.matched:,}",
            f"eligible {row.eligible:,}",
            human_bytes(row.bytes),
            human_duration(elapsed),
        ]
    elif status == "CLEAN":
        marker = "OK"
        tokens = [
            f"checked {row.checked:,}",
            f"matched {row.matched:,}",
            f"too-new {row.too_new:,}",
            f"pruned {row.skipped:,}",
            human_duration(elapsed),
        ]
    elif status == "MISSING":
        marker = "MISS"
        tokens = ["not installed / target not present"]
    elif status == "SKIPPED":
        marker = "SKIP"
        tokens = [row.message or "skipped"]
    else:
        marker = "ERR"
        tokens = [row.message or "scan error"]

    width = _terminal_width()
    if width < 78:
        label_width = max(10, width - 14)
        lines = [f"[{marker}] {idx:>2}/{total:<2} {_shorten_right(label, label_width)}"]
        lines.extend(_pack_detail_lines(tokens, width))
        return lines

    pct = int((idx / total) * 100) if total else 100
    detail = " | ".join(tokens)
    fixed = f"[{marker}] {_progress_bar(idx, total)} {idx}/{total} {pct:3d}% | "
    remaining = max(16, width - len(fixed) - 1)
    # Prefer preserving the detail fields; shorten the label first.
    if len(label) + 3 + len(detail) > remaining:
        label_room = max(12, remaining - len(detail) - 3)
        label = _shorten_right(label, label_room)
    line = fixed + label + " | " + detail
    if len(line) <= width - 1:
        return [line]
    # Very detailed desktop rows may still exceed the width; wrap details instead of
    # truncating counters/durations.
    head = _shorten_right(f"[{marker}] {idx}/{total} {pct:3d}% | {label}", width - 1)
    return [head, *_pack_detail_lines(tokens, width)]


class LiveProgress:
    """Persistent realtime single-line progress renderer.

    There is deliberately no fast | / - \\ spinner. A slowly filling bar is much
    easier to perceive on Termux/phone terminals, especially when the actual scan
    finishes in only a few hundred milliseconds.
    """

    def __init__(self, enabled: bool = True, interval: float = PROGRESS_FRAME_INTERVAL) -> None:
        force = os.getenv("BERSIHIN_FORCE_PROGRESS") == "1"
        self.enabled = bool(
            enabled
            and (sys.stdout.isatty() or force)
            and os.getenv("TERM", "") != "dumb"
        )
        self.interval = max(0.08, float(interval))
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._paused = threading.Event()
        self._thread: threading.Thread | None = None
        self._message_factory: Callable[[int], str] | None = None
        self._message = ""
        self._frame = 0
        self._started = 0.0

    @property
    def elapsed(self) -> float:
        return max(0.0, time.monotonic() - self._started) if self._started else 0.0

    def _clear_line(self) -> None:
        if self.enabled:
            print("\r\033[2K", end="", flush=True)

    def _render(self) -> None:
        if not self.enabled or self._paused.is_set():
            return
        with self._lock:
            frame = self._frame
            self._frame += 1
            factory = self._message_factory
            message = factory(frame) if factory is not None else self._message
        width = max(16, _terminal_width() - 1)
        line = _shorten_right(message, width)
        self._clear_line()
        print(line, end="", flush=True)

    def _loop(self) -> None:
        while not self._stop.wait(self.interval):
            self._render()

    def start(self, message: str | None = None,
              factory: Callable[[int], str] | None = None) -> None:
        if self._thread and self._thread.is_alive():
            self.update(message=message, factory=factory)
            return
        with self._lock:
            self._message = message or "Working..."
            self._message_factory = factory
            self._frame = 0
            self._started = time.monotonic()
        if not self.enabled:
            return
        self._paused.clear()
        self._stop.clear()
        self._render()
        self._thread = threading.Thread(
            target=self._loop,
            daemon=True,
            name="bersihin-progress",
        )
        self._thread.start()

    def update(self, message: str | None = None,
               factory: Callable[[int], str] | None = None) -> None:
        self._paused.clear()
        with self._lock:
            if message is not None:
                self._message = message
            if factory is not None:
                self._message_factory = factory
        if self.enabled:
            self._render()

    def ensure_visible(self, minimum_seconds: float) -> None:
        if not self.enabled or not self._started:
            return
        remaining = max(0.0, minimum_seconds - self.elapsed)
        if remaining:
            deadline = time.monotonic() + remaining
            while time.monotonic() < deadline:
                time.sleep(min(self.interval, max(0.0, deadline - time.monotonic())))

    def suspend_line(self) -> None:
        if self.enabled:
            self._paused.set()
            self._clear_line()

    def stop(self, final: str | None = None, clear: bool = False) -> None:
        if self._thread and self._thread.is_alive():
            self._stop.set()
            self._thread.join(timeout=max(0.30, self.interval * 4))
        self._thread = None
        if self.enabled:
            self._clear_line()
            if final is not None and not clear:
                print(_shorten_right(final, _terminal_width() - 1), flush=True)
        elif final is not None and not clear:
            print(final, flush=True)
        self._stop.clear()
        self._paused.clear()
        self._message_factory = None
        self._started = 0.0



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
    exclude_names: tuple[str, ...] = ()
    dirs_only: bool = False


@dataclasses.dataclass
class Candidate:
    path: Path
    label: str
    category: str
    size: int
    mtime: float


@dataclasses.dataclass
class RuleScan:
    label: str
    category: str
    root: str
    status: str
    checked: int = 0
    matched: int = 0
    eligible: int = 0
    too_new: int = 0
    bytes: int = 0
    skipped: int = 0
    errors: int = 0
    message: str = ""


@dataclasses.dataclass
class Result:
    scanned_bytes: int = 0
    removed_bytes: int = 0
    candidates: int = 0
    removed: int = 0
    skipped: int = 0
    errors: int = 0


PROTECTED_NAMES = {"windows", "system32", "program files", "program files (x86)"}
PROJECT_MARKERS = (
    ".git", "pyproject.toml", "requirements.txt", "setup.py", "package.json",
    "Cargo.toml", "go.mod", "composer.json", "pom.xml", "build.gradle",
)
PROJECT_CACHE_DIRS = (
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".parcel-cache", ".turbo",
)


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
        family, name, distro = "termux", "Termux", "Android/Termux"
    elif is_wsl:
        family, name = "wsl", "Windows Subsystem for Linux"
        distro = osr.get("PRETTY_NAME") or osr.get("NAME") or "WSL Linux"
    elif is_windows:
        family, name, distro = "windows", "Windows", platform.platform()
    elif is_macos:
        family, name = "macos", "macOS"
        distro = f"macOS {platform.mac_ver()[0]}".strip()
    elif is_linux:
        family, name = "linux", "Linux"
        distro = osr.get("PRETTY_NAME") or osr.get("NAME") or platform.platform()
    elif is_bsd:
        family, name, distro = "bsd", platform.system(), platform.platform()
    else:
        family = "posix" if os.name == "posix" else "other"
        name, distro = platform.system() or os.name, platform.platform()

    detected_temp = (Path(prefix) / "tmp") if (is_termux and prefix) else Path(tempfile.gettempdir())

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
        temp=detected_temp,
        admin=_is_admin_windows() if is_windows else _is_admin_posix(),
    )


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
        if p.drive:
            protected.add(Path(p.drive + "\\"))
    if p in protected:
        return True
    return bool(p.name.lower() in PROTECTED_NAMES and p.parent == Path(p.anchor))


def _matches(path: Path, patterns: Sequence[str]) -> bool:
    return any(fnmatch.fnmatch(path.name, pat) for pat in patterns)


def _excluded(path: Path, excludes: Sequence[str]) -> bool:
    return any(fnmatch.fnmatch(path.name, pat) for pat in excludes)


def _old_enough(path: Path, age_days: int, now: float) -> bool:
    if age_days <= 0:
        return True
    try:
        return now - os.stat(path, follow_symlinks=False).st_mtime >= age_days * 86400
    except OSError:
        return False


def _candidate_from(path: Path, rule: Rule) -> Candidate:
    return Candidate(path, rule.label, rule.category, path_size(path), path.stat().st_mtime)


def scan_rule(rule: Rule, env: Environment,
              progress_cb: Callable[[RuleScan, Path | None, float], None] | None = None
              ) -> tuple[list[Candidate], RuleScan]:
    root = rule.root.expanduser()
    statrow = RuleScan(rule.label, rule.category, str(root), "CLEAN")
    started = time.time()
    last_emit = 0.0

    def emit(current: Path | None = None, force: bool = False) -> None:
        nonlocal last_emit
        if progress_cb is None:
            return
        now_mono = time.monotonic()
        if force or statrow.checked <= 1 or now_mono - last_emit >= 0.08:
            last_emit = now_mono
            progress_cb(statrow, current, time.time() - started)

    if not root.exists():
        statrow.status = "MISSING"
        statrow.message = "target does not exist"
        emit(root, True)
        return [], statrow
    if root.is_symlink():
        statrow.status = "SKIPPED"
        statrow.message = "target is a symlink"
        emit(root, True)
        return [], statrow
    if _is_dangerous_target(root, env):
        statrow.status = "SKIPPED"
        statrow.message = "protected root"
        emit(root, True)
        return [], statrow

    now = time.time()
    found: list[Candidate] = []
    seen: set[str] = set()

    def consider(p: Path) -> bool:
        """Return True when a matched directory should be pruned from traversal."""
        statrow.checked += 1
        try:
            if p.is_symlink():
                statrow.skipped += 1
                emit(p)
                return p.is_dir()
            if _excluded(p, rule.exclude_names):
                statrow.skipped += 1
                emit(p)
                return p.is_dir()
            if not _matches(p, rule.patterns):
                emit(p)
                return False
            statrow.matched += 1
            if rule.owner_only and not _same_owner(p):
                statrow.skipped += 1
                emit(p)
                return False
            if not _old_enough(p, rule.min_age_days, now):
                statrow.too_new += 1
                emit(p)
                return False
            if _is_dangerous_target(p, env):
                statrow.skipped += 1
                emit(p)
                return False
            key = os.path.normcase(str(p.absolute()))
            if key in seen:
                statrow.skipped += 1
                emit(p)
                return False
            seen.add(key)
            cand = _candidate_from(p, rule)
            found.append(cand)
            statrow.eligible += 1
            statrow.bytes += cand.size
            emit(p, True)
            return p.is_dir()
        except (OSError, PermissionError):
            statrow.errors += 1
            statrow.skipped += 1
            emit(p)
            return False

    try:
        if rule.recursive and rule.patterns != ("*",):
            for base, dirs, files in os.walk(root, topdown=True, followlinks=False):
                kept_dirs = []
                for name in dirs:
                    p = Path(base) / name
                    prune = consider(p)
                    if not prune and not p.is_symlink():
                        kept_dirs.append(name)
                dirs[:] = kept_dirs
                if not rule.dirs_only:
                    for name in files:
                        consider(Path(base) / name)
        else:
            for child in root.iterdir():
                consider(child)
    except (OSError, PermissionError) as exc:
        statrow.status = "ERROR"
        statrow.errors += 1
        statrow.message = str(exc)
        emit(root, True)
        return found, statrow

    if found:
        statrow.status = "FOUND"
    emit(root, True)
    return found, statrow


def _add_rule(rules: list[Rule], label: str, category: str, path: Path | str | None,
              *, age: int = 0, patterns: tuple[str, ...] = ("*",),
              recursive: bool = True, owner_only: bool = False, note: str = "",
              exclude_names: tuple[str, ...] = (), dirs_only: bool = False) -> None:
    if not path:
        return
    rules.append(Rule(label, category, Path(path).expanduser(), patterns, age,
                      recursive, owner_only, note, exclude_names, dirs_only))


def _command_output(args: Sequence[str]) -> str:
    try:
        cp = subprocess.run(args, capture_output=True, text=True, timeout=8,
                            encoding="utf-8", errors="replace")
        return cp.stdout.strip() if cp.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def discover_project_roots(env: Environment, limit: int = 16) -> list[Path]:
    home = env.home
    candidates: list[Path] = [Path.cwd()]
    for name in ("projects", "src", "apps", "code", "workspace", "repos", "dev"):
        candidates.append(home / name)
    try:
        for child in home.iterdir():
            if len(candidates) >= limit * 3:
                break
            if not child.is_dir() or child.is_symlink() or child.name.startswith("."):
                continue
            try:
                if any((child / marker).exists() for marker in PROJECT_MARKERS):
                    candidates.append(child)
            except OSError:
                continue
    except OSError:
        pass

    result: list[Path] = []
    seen: set[str] = set()
    for p in candidates:
        try:
            p = p.expanduser().absolute()
        except OSError:
            continue
        key = os.path.normcase(str(p))
        if key in seen or p == home.absolute() or not p.exists() or _is_dangerous_target(p, env):
            continue
        seen.add(key)
        result.append(p)
        if len(result) >= limit:
            break
    return result


def _dedupe_rules(rules: Sequence[Rule]) -> list[Rule]:
    out: list[Rule] = []
    seen: set[tuple[str, str, tuple[str, ...], int]] = set()
    for rule in rules:
        key = (
            rule.category, os.path.normcase(str(rule.root.absolute())), rule.patterns,
            rule.min_age_days, rule.recursive, rule.owner_only, rule.exclude_names, rule.dirs_only,
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(rule)
    return out


def build_rules(env: Environment, args: argparse.Namespace) -> list[Rule]:
    rules: list[Rule] = []
    home = env.home
    age = max(0, args.older_than)
    xdg_cache = Path(os.getenv("XDG_CACHE_HOME") or (home / ".cache"))

    # Temporary data.
    shared_posix_temp_as_root = (
        os.name == "posix" and env.admin and not env.is_termux
        and env.temp in {Path("/tmp"), Path("/var/tmp")}
    )
    if not shared_posix_temp_as_root:
        _add_rule(rules, "Temporary files", "temp", env.temp,
                  age=age, owner_only=not env.is_windows,
                  note="Old temporary entries")
    if env.is_termux and env.prefix:
        _add_rule(rules, "Termux temporary files", "temp", Path(env.prefix) / "tmp",
                  age=age, owner_only=True, note="Termux PREFIX temporary entries")

    # Python and common development caches.
    if env.is_windows:
        local = os.getenv("LOCALAPPDATA")
        _add_rule(rules, "pip cache", "dev", Path(local) / "pip" / "Cache" if local else None)
    elif env.is_macos:
        _add_rule(rules, "pip cache", "dev", home / "Library" / "Caches" / "pip")
    else:
        _add_rule(rules, "pip cache", "dev", xdg_cache / "pip")

    for root in discover_project_roots(env):
        label = f"Project caches ({root.name or 'cwd'})"
        _add_rule(
            rules, label, "dev", root, patterns=PROJECT_CACHE_DIRS,
            recursive=True, owner_only=True,
            note="Python/test/build cache directories",
            exclude_names=(".git", ".hg", ".svn", "node_modules", ".venv", "venv", "env",
                           "dist", "build", ".tox", ".nox", "vendor"),
            dirs_only=True,
        )
        # Known nested caches that are safe to rebuild.
        for rel, sublabel in (
            ("node_modules/.cache", "Node project cache"),
            (".next/cache", "Next.js cache"),
            (".vite", "Vite cache"),
        ):
            _add_rule(rules, f"{sublabel} ({root.name})", "dev", root / rel,
                      owner_only=True)

    npm_cache = _command_output(["npm", "config", "get", "cache"]) if shutil.which("npm") else ""
    npm_root = Path(npm_cache) if npm_cache and npm_cache.lower() not in {"undefined", "null"} else home / ".npm"
    _add_rule(rules, "npm content cache", "dev", npm_root / "_cacache")
    _add_rule(rules, "npm logs", "dev", npm_root / "_logs", age=age)
    _add_rule(rules, "npx temporary packages", "dev", npm_root / "_npx", age=age)

    yarn_cache = _command_output(["yarn", "cache", "dir"]) if shutil.which("yarn") else ""
    _add_rule(rules, "Yarn cache", "dev", yarn_cache or (xdg_cache / "yarn"))
    _add_rule(rules, "pnpm cache", "dev", xdg_cache / "pnpm")

    if env.is_windows:
        local = os.getenv("LOCALAPPDATA")
        if local:
            _add_rule(rules, "pnpm cache", "dev", Path(local) / "pnpm-cache")
            _add_rule(rules, "NuGet HTTP cache", "dev", Path(local) / "NuGet" / "v3-cache")
            _add_rule(rules, "DirectX shader cache", "usercache", Path(local) / "D3DSCache")
            _add_rule(rules, "Explorer thumbnail cache", "usercache", Path(local) / "Microsoft/Windows/Explorer",
                      patterns=("thumbcache_*.db", "iconcache_*.db"), recursive=False)
        _add_rule(rules, "Scoop download cache", "packages", home / "scoop" / "cache")

    if env.is_macos:
        _add_rule(rules, "Homebrew download cache", "packages", home / "Library" / "Caches" / "Homebrew")

    if shutil.which("go"):
        gocache = _command_output(["go", "env", "GOCACHE"])
        if gocache and gocache.lower() != "off":
            _add_rule(rules, "Go build cache", "dev", gocache)

    _add_rule(rules, "Cargo registry downloads", "dev", home / ".cargo" / "registry" / "cache")

    if shutil.which("composer"):
        comp = _command_output(["composer", "config", "cache-dir", "--global"])
        if comp:
            _add_rule(rules, "Composer cache", "dev", comp)

    gradle = home / ".gradle" / "caches"
    if gradle.exists():
        try:
            for p in gradle.glob("build-cache-*"):
                _add_rule(rules, "Gradle build cache", "dev", p)
        except OSError:
            pass

    # Package download caches.
    if env.is_termux and env.prefix:
        _add_rule(rules, "Termux APT archives", "packages", Path(env.prefix) / "var/cache/apt/archives",
                  patterns=("*.deb",), recursive=False,
                  note="Downloaded package archives; installed packages are untouched")
    if args.system:
        if env.family in {"linux", "wsl"}:
            _add_rule(rules, "APT package archives", "system", "/var/cache/apt/archives",
                      patterns=("*.deb",), recursive=False)
            _add_rule(rules, "DNF cache", "system", "/var/cache/dnf")
            _add_rule(rules, "APK cache", "system", "/var/cache/apk")
            _add_rule(rules, "Pacman package cache", "system", "/var/cache/pacman/pkg",
                      patterns=("*.pkg.tar.*",), recursive=False)
        if env.is_windows:
            windir = os.getenv("WINDIR") or r"C:\Windows"
            _add_rule(rules, "Windows Temp", "system", Path(windir) / "Temp",
                      age=age, owner_only=not env.admin)

    # Safe user cache extras in the default profile.
    if not env.is_windows and not env.is_macos:
        _add_rule(rules, "Thumbnail cache", "usercache", xdg_cache / "thumbnails")
        _add_rule(rules, "Fontconfig cache", "usercache", xdg_cache / "fontconfig")
    if env.is_termux:
        _add_rule(rules, "Termux Python cache", "usercache", xdg_cache / "python")

    # Trash and browsers remain explicit unless --full is used.
    if args.trash:
        if env.is_windows:
            pass
        elif env.is_macos:
            _add_rule(rules, "Trash", "trash", home / ".Trash")
        else:
            _add_rule(rules, "Trash files", "trash", home / ".local/share/Trash/files")
            _add_rule(rules, "Trash metadata", "trash", home / ".local/share/Trash/info")

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
                                _add_rule(rules, f"Browser {sub}", "browsers", profile/sub)
            for ffroot in [
                Path(local) / "Mozilla/Firefox/Profiles" if local else None,
                Path(roaming) / "Mozilla/Firefox/Profiles" if roaming else None,
            ]:
                if ffroot and ffroot.exists():
                    for profile in ffroot.glob("*"):
                        _add_rule(rules, "Firefox cache", "browsers", profile/"cache2")
        elif env.is_macos:
            for p in [home/"Library/Caches/Google/Chrome", home/"Library/Caches/Microsoft Edge",
                      home/"Library/Caches/Firefox"]:
                _add_rule(rules, "Browser cache", "browsers", p)
        else:
            for p in [home/".cache/google-chrome", home/".cache/chromium", home/".cache/microsoft-edge",
                      home/".cache/mozilla/firefox"]:
                _add_rule(rules, "Browser cache", "browsers", p)

    if args.aggressive:
        known_excludes = (
            "pip", "yarn", "pnpm", "thumbnails", "fontconfig",
            "google-chrome", "chromium", "microsoft-edge", "mozilla",
        )
        if env.is_windows:
            local = os.getenv("LOCALAPPDATA")
            if local:
                _add_rule(rules, "Generic user Temp", "aggressive", Path(local) / "Temp", age=age)
        elif env.is_macos:
            _add_rule(rules, "Generic user caches", "aggressive", home / "Library/Caches",
                      age=age, exclude_names=known_excludes)
        else:
            _add_rule(rules, "Generic user caches", "aggressive", xdg_cache,
                      age=age, exclude_names=known_excludes)

    return _dedupe_rules(rules)


def _dedupe_candidates(candidates: Sequence[Candidate]) -> list[Candidate]:
    # Prefer parent candidates so a cache directory is removed once rather than
    # counting/removing descendants separately.
    ordered = sorted(candidates, key=lambda c: (len(c.path.parts), str(c.path).lower()))
    out: list[Candidate] = []
    parents: list[str] = []
    for cand in ordered:
        key = os.path.normcase(str(cand.path.absolute()))
        if any(key == parent or key.startswith(parent + os.sep) for parent in parents):
            continue
        out.append(cand)
        parents.append(key)
    return out


def collect_candidates(rules: Sequence[Rule], env: Environment,
                       categories: set[str] | None = None,
                       progress: bool = False,
                       verbose: bool = False) -> tuple[list[Candidate], list[RuleScan]]:
    raw: list[Candidate] = []
    scans: list[RuleScan] = []
    selected = [r for r in rules if not categories or r.category in categories]
    total = len(selected)
    live = LiveProgress(enabled=progress)
    all_started = time.time()
    hidden_missing = 0

    # Shared state is read by the animation thread. The callback updates counters
    # while os.walk is still running, so checked/matched numbers visibly increase.
    state: dict[str, object] = {
        "idx": 0,
        "label": "Preparing scan",
        "checked": 0,
        "eligible": 0,
        "matched": 0,
        "current": None,
        "target_started": time.time(),
        "visual_pct": 0.0,
    }

    def factory(frame: int) -> str:
        elapsed = time.time() - float(state["target_started"])
        actual_pct = (int(state["idx"]) / total * 100.0) if total else 100.0
        visual = float(state["visual_pct"])
        if actual_pct > visual:
            visual = min(actual_pct, visual + PROGRESS_MAX_STEP_PERCENT)
            state["visual_pct"] = visual
        return _live_progress_text(
            "Scanning",
            int(state["idx"]),
            total,
            str(state["label"]),
            checked=int(state["checked"]),
            eligible=int(state["eligible"]),
            matched=int(state["matched"]),
            elapsed=elapsed,
            frame=frame,
            current=state["current"] if isinstance(state["current"], Path) else None,
            visual_pct=visual,
        )

    if progress:
        live.start(factory=factory)

    try:
        for idx, rule in enumerate(selected, 1):
            item_started = time.time()
            state.update({
                "idx": idx - 1,
                "label": rule.label,
                "checked": 0,
                "eligible": 0,
                "matched": 0,
                "current": rule.root,
                "target_started": item_started,
            })
            if progress:
                live.update(factory=factory)

            def on_progress(row: RuleScan, current: Path | None, elapsed: float) -> None:
                state.update({
                    "idx": idx - 1,
                    "label": rule.label,
                    "checked": row.checked,
                    "eligible": row.eligible,
                    "matched": row.matched,
                    "current": current,
                })

            found, row = scan_rule(rule, env, progress_cb=on_progress if progress else None)
            elapsed = time.time() - item_started
            raw.extend(found)
            scans.append(row)

            state.update({
                "idx": idx,
                "label": rule.label,
                "checked": row.checked,
                "eligible": row.eligible,
                "matched": row.matched,
                "current": None,
            })

            if row.status == "MISSING" and not verbose:
                hidden_missing += 1
                continue

            # Permanent rows remain informative, but the animation thread is not
            # restarted for each target. Clear its current frame, print, continue.
            if progress or verbose:
                live.suspend_line()
                for line in _final_scan_lines(idx, total, row, elapsed):
                    print(line, flush=True)
                if progress:
                    live.update(factory=factory)

        if progress:
            state.update({
                "idx": total,
                "label": "Finalizing scan",
                "checked": sum(s.checked for s in scans),
                "eligible": sum(s.eligible for s in scans),
                "matched": sum(s.matched for s in scans),
                "current": None,
                "target_started": all_started,
            })
            live.update(factory=factory)
            # A very fast real scan can complete before the human eye sees the bar.
            # Keep the interactive display briefly and let visual_pct catch up to 100.
            deadline = time.monotonic() + MIN_SCAN_ANIMATION_SECONDS
            while live.enabled and float(state["visual_pct"]) < 100.0 and time.monotonic() < deadline:
                time.sleep(PROGRESS_FRAME_INTERVAL)
            state["visual_pct"] = 100.0
            live.update(factory=factory)
            time.sleep(0.16)
    finally:
        live.stop(clear=True)

    if progress:
        elapsed = time.time() - all_started
        print(
            f"[+] Scan complete: {total}/{total} target(s), 100% | {human_duration(elapsed)}",
            flush=True,
        )
        if hidden_missing:
            print(
                f"[*] {hidden_missing} unavailable/not-installed target(s) hidden; use --verbose to show them.",
                flush=True,
            )

    return _dedupe_candidates(raw), scans


def delete_candidate(cand: Candidate) -> tuple[bool, str]:
    p = cand.path
    try:
        if p.is_symlink():
            return False, "symlink skipped"
        if p.is_dir():
            shutil.rmtree(p)
        else:
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
        flags = 0x1 | 0x2 | 0x4
        rc = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, flags)
        return rc == 0, "" if rc == 0 else f"Shell return code {rc}"
    except Exception as exc:
        return False, str(exc)


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
        err("This copy is installed as a Python package. Update the package/source installation instead.")
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
        ok(f"Updated {__version__} -> {remote_version}")
        info(f"Backup: {backup}")
        return 0
    except OSError as exc:
        err(f"Cannot replace {current}: {exc}")
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass
        return 1


def uninstall_self(yes: bool) -> int:
    current = Path(__file__).resolve()
    home = Path.home()
    targets = [current, home / ".local/bin/bersihin", home / ".local/share/bersihin/bersihin.py"]
    if os.name == "nt":
        local = os.getenv("LOCALAPPDATA")
        if local:
            targets += [Path(local) / "Bersihin/bersihin.py", Path(local) / "Programs/Bersihin/bin/bersihin.cmd"]
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


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="bersihin",
        description="Safe and informative cleaner for Windows, Linux, Termux, WSL, macOS and POSIX systems.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--dry-run", "--scan", action="store_true", dest="dry_run",
                   help="Scan and show reclaimable data without deleting anything")
    p.add_argument("--yes", "-y", action="store_true", help="Do not ask for confirmation")
    p.add_argument("--older-than", type=int, default=2,
                   help="Minimum age in days for temp/log/generic cache entries")
    p.add_argument("--category", action="append",
                   choices=["temp", "dev", "packages", "usercache", "system", "trash", "browsers", "aggressive"],
                   help="Only process selected category; may be repeated")
    p.add_argument("--system", action="store_true", help="Include supported system/package caches; may require admin/root")
    p.add_argument("--trash", action="store_true", help="Include user Trash / Windows Recycle Bin")
    p.add_argument("--browsers", action="store_true", help="Include browser cache directories; close browsers first")
    p.add_argument("--aggressive", action="store_true", help="Include broad user cache directories")
    p.add_argument("--full", action="store_true",
                   help="Full profile: enable system + trash + browsers + aggressive scopes")
    p.add_argument("--json", action="store_true", help="Print scan/result data as JSON")
    p.add_argument("--verbose", "-v", action="store_true", help="List every final candidate path")
    p.add_argument("--quiet", "-q", "--no-progress", action="store_true",
                   help="Disable realtime scan/cleanup progress")
    p.add_argument("--force-progress", action="store_true",
                   help="Force ANSI progress animation even when stdout is not detected as a TTY")
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
    for name in ["git", "curl", "wget", "pip", "pip3", "npm", "yarn", "pnpm", "go", "cargo", "composer", "docker"]:
        print(f"  {name:<10} {shutil.which(name) or '-'}")
    return 0


def _profile_text(args: argparse.Namespace) -> str:
    enabled = []
    if args.system: enabled.append("system")
    if args.trash: enabled.append("trash")
    if args.browsers: enabled.append("browsers")
    if args.aggressive: enabled.append("aggressive")
    return "full" if args.full else ("default" + (" + " + " + ".join(enabled) if enabled else ""))


def _scan_summary(scans: Sequence[RuleScan]) -> dict[str, int]:
    return {
        "targets": len(scans),
        "found": sum(1 for s in scans if s.status == "FOUND"),
        "clean": sum(1 for s in scans if s.status == "CLEAN"),
        "missing": sum(1 for s in scans if s.status == "MISSING"),
        "skipped": sum(1 for s in scans if s.status in {"SKIPPED", "ERROR"}),
        "checked_entries": sum(s.checked for s in scans),
    }


def _category_summary(candidates: Sequence[Candidate]) -> dict[str, tuple[int, int]]:
    out: dict[str, tuple[int, int]] = {}
    for cand in candidates:
        count, size = out.get(cand.category, (0, 0))
        out[cand.category] = (count + 1, size + cand.size)
    return out


def _display_path(path: Path, home: Path) -> str:
    try:
        absolute = path.expanduser().absolute()
        home_abs = home.expanduser().absolute()
        if absolute == home_abs:
            return "~"
        try:
            rel = absolute.relative_to(home_abs)
            return str(Path("~") / rel)
        except ValueError:
            return str(absolute)
    except OSError:
        return str(path)


def _print_candidate_preview(candidates: Sequence[Candidate], env: Environment,
                             limit: int = 10) -> None:
    if not candidates:
        return
    ranked = sorted(candidates, key=lambda c: (c.size, str(c.path).lower()), reverse=True)
    shown = ranked[:limit]
    print("\nWill remove:")
    width = _terminal_width()
    for cand in shown:
        label = _shorten_right(_friendly_label(cand.label), 22 if width < 78 else 30)
        ptext = _display_path(cand.path, env.home)
        if width < 78:
            max_path = max(18, width - 6)
            print(f"  {human_bytes(cand.size):>9}  {label}")
            print(f"             {_shorten_middle(ptext, max_path)}")
        else:
            print(f"  {human_bytes(cand.size):>10}  {label:<30} {_shorten_middle(ptext, max(24, width - 48))}")
    remaining = len(ranked) - len(shown)
    if remaining > 0:
        rest_size = sum(c.size for c in ranked[len(shown):])
        print(f"  ... and {remaining} more item(s), {human_bytes(rest_size)}")


def _print_category_summary(candidates: Sequence[Candidate]) -> None:
    grouped = _category_summary(candidates)
    if not grouped:
        return
    names = {
        "temp": "Temporary",
        "dev": "Developer caches",
        "packages": "Package downloads",
        "usercache": "User caches",
        "system": "System caches",
        "trash": "Trash",
        "browsers": "Browser caches",
        "aggressive": "Generic caches",
    }
    print("\nReclaimable by category:")
    for category, (count, size) in sorted(grouped.items(), key=lambda kv: kv[1][1], reverse=True):
        label = names.get(category, category)
        print(f"  {label:<22} {count:>6} item(s)  {human_bytes(size):>12}")


def _scan_reason_summary(scans: Sequence[RuleScan]) -> tuple[int, int, int, int]:
    matched = sum(s.matched for s in scans)
    eligible = sum(s.eligible for s in scans)
    too_new = sum(s.too_new for s in scans)
    skipped = sum(s.skipped for s in scans)
    return matched, eligible, too_new, skipped


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.force_progress:
        os.environ["BERSIHIN_FORCE_PROGRESS"] = "1"
    env = detect_environment()

    if args.update:
        return self_update()
    if args.uninstall:
        return uninstall_self(args.yes)
    if args.doctor:
        return doctor(env)
    if args.older_than < 0:
        err("--older-than cannot be negative")
        return 2

    if args.full:
        args.system = True
        args.trash = True
        args.browsers = True
        args.aggressive = True

    selected_categories = set(args.category or [])
    for category, attr in (("system", "system"), ("trash", "trash"), ("browsers", "browsers"), ("aggressive", "aggressive")):
        if category in selected_categories:
            setattr(args, attr, True)

    rules = build_rules(env, args)
    categories = selected_categories or None

    if args.list_targets:
        banner()
        info(f"Detected: {env.name} | {env.distro}")
        info(f"Profile: {_profile_text(args)} | Age threshold: {args.older_than} day(s)")
        for idx, rule in enumerate([r for r in rules if not categories or r.category in categories], 1):
            print(f"{idx:02d}. [{rule.category:<10}] {rule.label}")
            print(f"    {rule.root}")
            if rule.note:
                print(f"    {rule.note}")
        return 0

    if not args.json:
        banner()
        info(f"Platform : {env.name} | {env.distro} | {platform.machine()}")
        info(f"Profile  : {_profile_text(args)}")
        info(f"Mode     : {'scan only (dry-run)' if args.dry_run else 'cleanup'}")
        info(f"Age      : {args.older_than} day(s) for age-filtered targets")
        info(f"Privilege: {'Administrator/root' if env.admin else 'standard user'}")
        progress_active = (not args.quiet) and (sys.stdout.isatty() or args.force_progress)
        info(f"Progress : {'animated realtime' if progress_active else 'off/non-interactive'}")
        print("\nScanning targets:")

    started_scan = time.time()
    candidates, scans = collect_candidates(
        rules, env, categories,
        progress=(not args.json and not args.quiet),
        verbose=args.verbose,
    )
    scan_elapsed = time.time() - started_scan
    result = Result(scanned_bytes=sum(c.size for c in candidates), candidates=len(candidates))
    scanmeta = _scan_summary(scans)

    if args.json:
        payload = {
            "app": APP_NAME,
            "version": __version__,
            "environment": dataclasses.asdict(env),
            "profile": _profile_text(args),
            "dry_run": args.dry_run,
            "options": {
                "system": args.system, "trash": args.trash, "browsers": args.browsers,
                "aggressive": args.aggressive, "full": args.full,
                "older_than": args.older_than,
                "categories": sorted(categories) if categories else None,
            },
            "scan": {
                **scanmeta,
                "matched_entries": sum(s.matched for s in scans),
                "too_new_entries": sum(s.too_new for s in scans),
                "skipped_entries": sum(s.skipped for s in scans),
                "elapsed_seconds": round(scan_elapsed, 3),
            },
            "targets": [dataclasses.asdict(s) for s in scans],
            "candidates": [
                {"path": str(c.path), "label": c.label, "category": c.category, "size": c.size}
                for c in candidates
            ],
            "reclaimable_bytes": result.scanned_bytes,
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
        return 0

    matched, eligible, too_new, skipped_entries = _scan_reason_summary(scans)

    print("\nScan summary:")
    print(f"  Targets selected     : {scanmeta['targets']}")
    print(f"  Targets with data    : {scanmeta['found']}")
    print(f"  Targets already clean: {scanmeta['clean']}")
    print(f"  Targets not present  : {scanmeta['missing']}")
    print(f"  Targets skipped/error: {scanmeta['skipped']}")
    print(f"  Entries inspected    : {scanmeta['checked_entries']:,}")
    print(f"  Entries matched      : {matched:,}")
    print(f"  Too new (age filter) : {too_new:,}")
    print(f"  Entries pruned/skipped: {skipped_entries:,}")
    print(f"  Unique candidates    : {len(candidates):,}")
    print(f"  Reclaimable          : {human_bytes(result.scanned_bytes)}")
    print(f"  Scan time            : {human_duration(scan_elapsed)}")
    available_targets = scanmeta["found"] + scanmeta["clean"]
    print(f"  Available targets    : {available_targets}/{scanmeta['targets']}")
    if too_new:
        print(
            f"  Age-filter note      : {too_new:,} matched entr{'y' if too_new == 1 else 'ies'} "
            f"newer than {args.older_than} day(s)"
        )

    _print_category_summary(candidates)

    grouped: dict[str, tuple[int, int]] = {}
    for c in candidates:
        count, size = grouped.get(c.label, (0, 0))
        grouped[c.label] = (count + 1, size + c.size)
    if grouped and (args.verbose or len(grouped) <= 8):
        print("\nReclaimable by target:")
        for label, (count, size) in sorted(grouped.items(), key=lambda kv: kv[1][1], reverse=True):
            print(f"  {_friendly_label(label):<36} {count:>5} item(s)  {human_bytes(size):>12}")

    if args.verbose and candidates:
        print("\nCandidates:")
        for cand in sorted(candidates, key=lambda c: str(c.path).lower()):
            print(f"  [{cand.category:<10}] {human_bytes(cand.size):>10}  {cand.path}")

    if not candidates and not (args.trash and env.is_windows):
        print()
        ok("System is already clean for the selected profile.")
        if too_new and args.older_than > 0:
            info(
                f"{too_new:,} matched entr{'y was' if too_new == 1 else 'ies were'} skipped by the "
                f"{args.older_than}-day age filter."
            )
            info("Preview fresh cache/temp entries: bersihin --older-than 0 --dry-run")
        info("Broader preview: bersihin --full --dry-run")
        info("Add --verbose only when you want every missing target and candidate path.")
        return 0

    if args.dry_run:
        print()
        ok(f"Dry-run complete. Nothing deleted. Reclaimable: {human_bytes(result.scanned_bytes)}")
        return 0

    if args.full:
        warn("Full profile includes browser caches, Trash, generic user caches and supported system caches.")
    elif args.aggressive:
        warn("Aggressive mode includes broad user caches. Applications may rebuild them later.")
    if args.browsers:
        warn("Close browsers before cleaning to reduce locked-file errors.")
    if args.system and not env.admin:
        warn("Some system targets may require Administrator/root privileges.")

    _print_candidate_preview(candidates, env, limit=10)

    if not args.yes:
        ans = input(f"\nClean {len(candidates)} item(s), about {human_bytes(result.scanned_bytes)}? [y/N]: ").strip().lower()
        if ans not in {"y", "yes"}:
            info("Cancelled; nothing was deleted.")
            return 0

    try:
        free_before = shutil.disk_usage(env.home).free
    except OSError:
        free_before = 0

    print("\nCleaning:")
    started = time.time()
    total = len(candidates)
    live = LiveProgress(enabled=(not args.quiet))
    processed_bytes = 0
    clean_state: dict[str, object] = {
        "idx": 0,
        "label": "Preparing cleanup",
        "processed": 0,
        "current": None,
        "visual_pct": 0.0,
    }

    def clean_factory(frame: int) -> str:
        idx = int(clean_state["idx"])
        actual_pct = (idx / total * 100.0) if total else 100.0
        visual = float(clean_state["visual_pct"])
        if actual_pct > visual:
            visual = min(actual_pct, visual + PROGRESS_MAX_STEP_PERCENT)
            clean_state["visual_pct"] = visual
        pct = int(round(visual))
        label = _friendly_label(str(clean_state["label"]))
        bar = _progress_bar(visual, 100.0, pulse=frame)
        width = _terminal_width()
        size_text = f"{human_bytes(int(clean_state['processed']))}/{human_bytes(result.scanned_bytes)}"
        if width < 78:
            fixed = f"{bar} {pct:3d}% "
            suffix = f" | {idx}/{total} | {size_text}"
            room = max(8, width - len(fixed) - len(suffix) - 2)
            return fixed + _shorten_right(label, room) + suffix
        current = clean_state["current"]
        path_text = f" | {_shorten_middle(str(current), 30)}" if isinstance(current, Path) else ""
        return (
            f"{bar} {pct:3d}% | {idx}/{total} | {_shorten_right(label, 30)} | "
            f"{size_text}{path_text}"
        )

    if not args.quiet:
        live.start(factory=clean_factory)

    try:
        for idx, cand in enumerate(candidates, 1):
            item_started = time.time()
            label = _friendly_label(cand.label)
            clean_state.update({
                "idx": idx - 1,
                "label": label,
                "processed": processed_bytes,
                "current": cand.path,
            })
            if not args.quiet:
                live.update(factory=clean_factory)

            success, detail = delete_candidate(cand)
            item_elapsed = time.time() - item_started

            if success:
                result.removed += 1
                result.removed_bytes += cand.size
                processed_bytes += cand.size
                clean_state.update({
                    "idx": idx,
                    "label": label,
                    "processed": processed_bytes,
                    "current": None,
                })
                if args.verbose:
                    live.suspend_line()
                    print(
                        f"  [{idx:02d}/{total:02d}] REMOVED {human_bytes(cand.size):>10}  "
                        f"{_display_path(cand.path, env.home)}",
                        flush=True,
                    )
            else:
                result.errors += 1
                live.suspend_line()
                print(
                    f"[!] {idx}/{total} {label} | skipped: {detail or 'error'}",
                    flush=True,
                )
                clean_state.update({"idx": idx, "current": None})

        if not args.quiet:
            clean_state.update({
                "idx": total,
                "label": "Finalizing cleanup",
                "processed": processed_bytes,
                "current": None,
            })
            live.update(factory=clean_factory)
            live.ensure_visible(MIN_CLEAN_ANIMATION_SECONDS)
    finally:
        live.stop(clear=True)

    print(
        f"[+] Cleanup pass complete: {result.removed}/{total} item(s) processed | "
        f"{human_bytes(result.removed_bytes)} reclaimed",
        flush=True,
    )

    if args.trash and env.is_windows:
        success, detail = empty_windows_recycle_bin(dry_run=False)
        if success:
            ok("Windows Recycle Bin emptied.")
        else:
            result.errors += 1
            warn(f"Recycle Bin: {detail}")

    elapsed = time.time() - started
    try:
        free_after = shutil.disk_usage(env.home).free
    except OSError:
        free_after = 0
    disk_delta = max(0, free_after - free_before) if free_before and free_after else 0

    print("\nCleanup summary:")
    print(f"  Removed             : {result.removed} item(s)")
    print(f"  Estimated reclaimed : {human_bytes(result.removed_bytes)}")
    if disk_delta:
        print(f"  Filesystem delta    : {human_bytes(disk_delta)}")
        if disk_delta != result.removed_bytes:
            print("  Disk note           : filesystem block allocation can differ from file-size totals")
    print(f"  Failed/skipped      : {result.errors}")
    print(f"  Cleanup time        : {human_duration(elapsed)}")
    print(f"  Finished            : {dt.datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print()
    if result.errors:
        warn("Cleanup completed with some skipped/error items.")
        return 1
    ok("Cleanup completed successfully.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print()
        warn("Cancelled by user. No further targets/items will be processed.")
        raise SystemExit(130)
