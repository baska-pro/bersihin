#!/usr/bin/env bash
set -euo pipefail

REPO_RAW="https://raw.githubusercontent.com/baska-pro/bersihin/main/bersihin.py"
TEMP_SOURCE=""
SOURCE=""

cleanup() { [[ -n "$TEMP_SOURCE" ]] && rm -f "$TEMP_SOURCE" 2>/dev/null || true; }
trap cleanup EXIT

if command -v python3 >/dev/null 2>&1; then PYTHON_BIN="$(command -v python3)";
elif command -v python >/dev/null 2>&1; then PYTHON_BIN="$(command -v python)";
else echo "[-] Python 3 tidak ditemukan. Install Python 3.9+ terlebih dahulu." >&2; exit 1; fi

if ! "$PYTHON_BIN" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,9) else 1)'; then
  echo "[-] Dibutuhkan Python 3.9+; ditemukan: $($PYTHON_BIN --version 2>&1)" >&2; exit 1
fi

SCRIPT_SOURCE="${BASH_SOURCE[0]:-}"
if [[ -n "${BERSIHIN_SOURCE:-}" ]]; then
  [[ -f "$BERSIHIN_SOURCE" ]] || { echo "[-] BERSIHIN_SOURCE tidak ditemukan: $BERSIHIN_SOURCE" >&2; exit 1; }
  SOURCE="$BERSIHIN_SOURCE"
elif [[ -n "$SCRIPT_SOURCE" && -f "$SCRIPT_SOURCE" ]]; then
  HERE="$(cd -- "$(dirname -- "$SCRIPT_SOURCE")" 2>/dev/null && pwd)"
  [[ -f "$HERE/bersihin.py" ]] && SOURCE="$HERE/bersihin.py"
fi

if [[ -z "$SOURCE" ]]; then
  TEMP_SOURCE="$(mktemp "${TMPDIR:-/tmp}/bersihin.XXXXXX.py")"
  echo "[*] Mengunduh bersihin.py dari GitHub..."
  if command -v curl >/dev/null 2>&1; then curl -fsSL "$REPO_RAW" -o "$TEMP_SOURCE";
  elif command -v wget >/dev/null 2>&1; then wget -qO "$TEMP_SOURCE" "$REPO_RAW";
  else echo "[-] curl/wget tidak tersedia. Clone repository lalu jalankan ./install.sh." >&2; exit 1; fi
  SOURCE="$TEMP_SOURCE"
fi

"$PYTHON_BIN" -m py_compile "$SOURCE" || { echo "[-] Validasi bersihin.py gagal." >&2; exit 1; }

IS_TERMUX=false
if [[ -n "${PREFIX:-}" && "$PREFIX" == *com.termux* ]] || [[ -d /data/data/com.termux/files/usr ]]; then IS_TERMUX=true; fi
if $IS_TERMUX; then INSTALL_DIR="${PREFIX}/share/bersihin"; BIN_DIR="${PREFIX}/bin";
else INSTALL_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/bersihin"; BIN_DIR="$HOME/.local/bin"; fi
mkdir -p "$INSTALL_DIR" "$BIN_DIR"

INSTALL_TMP="$INSTALL_DIR/.bersihin.py.tmp.$$"
cp "$SOURCE" "$INSTALL_TMP"
chmod 644 "$INSTALL_TMP"
mv -f "$INSTALL_TMP" "$INSTALL_DIR/bersihin.py"

WRAPPER_TMP="$BIN_DIR/.bersihin.tmp.$$"
cat > "$WRAPPER_TMP" <<EOF
#!/usr/bin/env sh
exec "$PYTHON_BIN" "$INSTALL_DIR/bersihin.py" "\$@"
EOF
chmod 755 "$WRAPPER_TMP"
mv -f "$WRAPPER_TMP" "$BIN_DIR/bersihin"

printf '[+] Bersihin terpasang: %s\n' "$INSTALL_DIR/bersihin.py"
printf '[+] Command: %s\n' "$BIN_DIR/bersihin"
case ":$PATH:" in *":$BIN_DIR:"*) ;; *) echo "[!] $BIN_DIR belum ada di PATH."; echo "    export PATH=\"$BIN_DIR:\$PATH\"";; esac

echo "[*] Verifikasi instalasi..."
"$BIN_DIR/bersihin" --version
echo "[*] Cek platform: bersihin --doctor"
echo "[*] Scan aman:    bersihin --dry-run"
