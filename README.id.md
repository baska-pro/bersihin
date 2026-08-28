# Bersihin 🧼

**Bersihin** adalah CLI cleaner lintas platform untuk **Windows, Linux, Termux, WSL, macOS, BSD, dan POSIX lainnya**.

Versi publik tetap **2.0.2** sementara pengembangan di branch `main` disempurnakan. Model keamanan v2 tetap dipertahankan: Bersihin tidak menghapus seluruh `/tmp`, seluruh cache user, log sistem, paket terpasang, atau data Docker secara membabi-buta.

## Fitur Utama

- deteksi platform otomatis;
- progress realtime yang responsif di terminal interaktif;
- progress bar persen yang halus, bukan spinner cepat;
- layout compact otomatis untuk Termux/layar ponsel;
- statistik scan `checked`, `matched`, `eligible`, `too-new`, dan `skipped/pruned`;
- ringkasan target, kategori, jumlah entry, durasi, dan ukuran reclaimable;
- deteksi cache project otomatis;
- cache Python/pip, npm/npx, Yarn, pnpm, Go, Cargo, Composer, Gradle, dan tooling development lain;
- temp file dengan filter umur;
- opsi browser cache;
- opsi Trash / Recycle Bin;
- opsi package/system cache;
- mode aggressive terpisah;
- `--full` untuk preview/pembersihan opt-in yang lebih luas;
- output JSON untuk automation;
- `--doctor` dan `--list-targets`;
- tanpa dependency Python pihak ketiga.

## Instalasi

### Windows

```powershell
irm https://raw.githubusercontent.com/baska-pro/bersihin/main/install.ps1 | iex
```

Atau dari clone:

```powershell
.\install.ps1
```

### Linux / Termux / WSL / macOS

Install cepat:

```bash
curl -fsSL https://raw.githubusercontent.com/baska-pro/bersihin/main/install.sh | bash
```

`curl` tanpa `| bash` hanya menampilkan isi installer dan **belum menginstal Bersihin**.

Dari clone:

```bash
git clone https://github.com/baska-pro/bersihin.git
cd bersihin
chmod +x install.sh
./install.sh
```

Verifikasi:

```bash
bersihin --version
bersihin --doctor
bersihin --dry-run
```

## Penggunaan

Pembersihan normal:

```bash
bersihin
```

Preview aman:

```bash
bersihin --dry-run
```

Ikutkan file/cache baru yang biasanya tertahan filter umur:

```bash
bersihin --older-than 0 --dry-run
```

Preview lebih luas:

```bash
bersihin --full --dry-run
```

Scope tambahan:

```bash
bersihin --system --dry-run
bersihin --trash --dry-run
bersihin --browsers --dry-run
bersihin --aggressive --dry-run
```

Kategori tertentu:

```bash
bersihin --category temp --dry-run
bersihin --category dev --dry-run
```

Tampilkan semua kandidat dan target yang tidak tersedia:

```bash
bersihin --dry-run --verbose
```

Matikan progress realtime:

```bash
bersihin --no-progress
```

Paksa progress ANSI jika deteksi TTY terminal bermasalah:

```bash
bersihin --force-progress --dry-run
```

JSON:

```bash
bersihin --dry-run --json
```

Diagnostik:

```bash
bersihin --doctor
bersihin --list-targets
```

Update / uninstall:

```bash
bersihin --update
bersihin --uninstall
```

## Progress Realtime

Pada terminal interaktif, satu baris progress akan diperbarui selama scan:

```text
[====>           ]  28% Project cache | 10/36 | chk 124 | 83 ms
[==========>     ]  67% npm cache     | 24/36 | chk 382 | 410 ms
[================] 100% Finalizing scan
```

Pada Termux atau terminal sempit, nama target dipersingkat lebih dulu agar angka progress dan counter tetap terlihat.

Jika scan aslinya selesai sangat cepat, tampilan interaktif dibuat sedikit lebih halus supaya progress tetap sempat terlihat. Delay visual ini tidak diterapkan pada JSON, `--no-progress`, atau output non-interaktif.

## Ringkasan Scan

Setelah scan, Bersihin menjelaskan:

- berapa target yang dipilih;
- berapa target memiliki data;
- berapa target sudah bersih;
- berapa target tidak tersedia;
- jumlah entry diperiksa;
- jumlah entry cocok;
- jumlah yang terlalu baru menurut age filter;
- jumlah yang di-prune/skip;
- kandidat unik;
- ukuran data yang dapat dibersihkan;
- durasi scan.

Target `MISSING` tidak memenuhi layar secara default. Gunakan `--verbose` bila ingin melihat semuanya.

## Mode Keamanan

Default Bersihin tetap menghindari:

- filesystem root dan home directory itu sendiri;
- mengikuti symlink;
- file temp milik user lain;
- system log;
- package autoremove;
- Docker prune;
- browser cache tanpa opsi;
- Trash/Recycle Bin tanpa opsi;
- broad generic cache tanpa opsi.

Untuk scope yang lebih luas, lakukan preview terlebih dahulu:

```bash
bersihin --full --dry-run
```

Baca [docs/SAFETY.md](./docs/SAFETY.md).

## Status Pengembangan

Repository `main` sementara tetap memakai versi **2.0.2**. Perubahan pengembangan dicatat pada bagian **Unreleased** di `CHANGELOG.md`. Nomor versi baru dinaikkan setelah fitur ini benar-benar final.

## Lisensi

MIT License — lihat [LICENSE](./LICENSE).

Copyright © 2026 Baska ID. Maintainer: [@baska-pro](https://github.com/baska-pro).
