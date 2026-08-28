$ErrorActionPreference = "Stop"
$InstallDir = Join-Path $env:LOCALAPPDATA "Bersihin"
$BinDir = Join-Path $env:LOCALAPPDATA "Programs\Bersihin\bin"

$Answer = Read-Host "Hapus Bersihin? [y/N]"
if ($Answer -notmatch '^(y|yes)$') { Write-Host "Dibatalkan."; exit 0 }

Remove-Item -Recurse -Force -ErrorAction SilentlyContinue $InstallDir
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue (Split-Path -Parent $BinDir)

$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
$Parts = @($UserPath -split ';' | Where-Object { $_ -and $_ -ne $BinDir })
[Environment]::SetEnvironmentVariable("Path", ($Parts -join ';'), "User")
Write-Host "[+] Bersihin telah dihapus. Buka terminal baru untuk refresh PATH."
