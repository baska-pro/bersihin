# Bersihin 🧼

**Bersihin** adalah CLI cleaner lintas platform yang otomatis mendeteksi **Windows, Linux, Termux, WSL, macOS, BSD, dan POSIX lainnya**.

Versi **2.0.2** merupakan maintenance release dari rewrite v2 dengan fokus utama pada keamanan: tidak lagi menghapus seluruh `/tmp`, `~/.cache`, log sistem, atau menjalankan `apt autoremove` secara otomatis.

> **Perbaikan v2.0.2:** quick installer Linux/Termux/WSL/macOS melalui `curl ... | bash` diperbaiki, installer sekarang diverifikasi otomatis, dan CI menguji mode install langsung maupun piped installer.

## Fitur Utama

- deteksi platform otomatis;
- dry-run / scan aman;
- cache Python/pip, npm, Yarn, pnpm, Go, Cargo, Composer, Gradle, NuGet;
- temp files dengan batas umur;
- hanya file milik user pada temp POSIX bersama;
- opsi browser cache;
- opsi Trash / Recycle Bin;
- opsi package/system cache;
- mode aggressive terpisah;
- output JSON untuk automation;
- `--doctor` untuk diagnosis platform;
- self-update dengan validasi syntax + backup;
- installer Windows dan Unix/Termux;
- tanpa dependency Python pihak ketiga.

## Instalasi

### Clone

```bash
git clone https://github.com/baska-pro/bersihin.git
cd bersihin
```

### Windows

Install cepat dari PowerShell:

```powershell
irm https://raw.githubusercontent.com/baska-pro/bersihin/main/install.ps1 | iex
```

Atau dari clone, PowerShell:

```powershell
.\install.ps1
```

atau jalankan `install.cmd`.

### Linux / Termux / WSL / macOS

Install cepat — command berikut **mengunduh sekaligus menjalankan** installer:

```bash
curl -fsSL https://raw.githubusercontent.com/baska-pro/bersihin/main/install.sh | bash
```

> Jika hanya menjalankan `curl -fsSL https://raw.githubusercontent.com/baska-pro/bersihin/main/install.sh` tanpa `| bash`, isi script hanya ditampilkan ke terminal dan Bersihin **belum terpasang**.

Jika ingin memeriksa installer lebih dulu:

```bash
curl -fsSL https://raw.githubusercontent.com/baska-pro/bersihin/main/install.sh -o install.sh
less install.sh
bash install.sh
```

Atau dari clone:

```bash
git clone https://github.com/baska-pro/bersihin.git
cd bersihin
chmod +x install.sh
./install.sh
```

Setelah instalasi:

```bash
hash -r 2>/dev/null || true
bersihin --version
bersihin --doctor
bersihin --dry-run --verbose
```

## Penggunaan

Cek hasil deteksi:

```bash
bersihin --doctor
```

Preview tanpa menghapus:

```bash
bersihin --dry-run
```

Pembersihan normal:

```bash
bersihin
```

Tanpa konfirmasi:

```bash
bersihin --yes
```

Tambahan opsional:

```bash
bersihin --browsers --dry-run
bersihin --trash --dry-run
bersihin --system --dry-run
bersihin --aggressive --dry-run
```

Kategori tertentu:

```bash
bersihin --category temp --dry-run
bersihin --category dev --dry-run
```

File temp minimal berumur 7 hari:

```bash
bersihin --older-than 7 --dry-run
```

Lihat semua path kandidat:

```bash
bersihin --dry-run --verbose
```

Lihat target/rule yang dipilih:

```bash
bersihin --list-targets
```

JSON:

```bash
bersihin --dry-run --json
```

Update:

```bash
bersihin --update
```

Uninstall:

```bash
bersihin --uninstall
```

## Mode Keamanan

Secara default Bersihin **tidak**:

- menjalankan `apt autoremove`;
- menghapus log sistem;
- menghapus seluruh cache user secara membabi-buta;
- membersihkan Recycle Bin/Trash tanpa opsi;
- membersihkan browser tanpa opsi;
- menjalankan Docker prune.

Scope tambahan harus dipilih sendiri dengan `--system`, `--trash`, `--browsers`, atau `--aggressive`.

Baca [docs/SAFETY.md](./docs/SAFETY.md).

## Lisensi

MIT License — lihat [LICENSE](./LICENSE).

Copyright © 2026 Baska ID. Maintainer: [@baska-pro](https://github.com/baska-pro).


## Migrasi dari v1

Jika sebelumnya memakai Bersihin Bash v1, baca [docs/MIGRATION_V1.md](./docs/MIGRATION_V1.md).
