#!/usr/bin/env bash
set -euo pipefail

IS_TERMUX=false
if [[ -n "${PREFIX:-}" && "$PREFIX" == *com.termux* ]] || [[ -d /data/data/com.termux/files/usr ]]; then
  IS_TERMUX=true
fi

if $IS_TERMUX; then
  INSTALL_DIR="${PREFIX}/share/bersihin"
  BIN="$PREFIX/bin/bersihin"
else
  INSTALL_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/bersihin"
  BIN="$HOME/.local/bin/bersihin"
fi

read -r -p "Hapus Bersihin? [y/N]: " ans
case "$ans" in y|Y|yes|YES) ;; *) echo "Dibatalkan."; exit 0;; esac
rm -f "$BIN"
rm -rf "$INSTALL_DIR"
echo "[+] Bersihin telah dihapus."
