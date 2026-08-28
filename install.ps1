$ErrorActionPreference = "Stop"
$RawSource = "https://raw.githubusercontent.com/baska-pro/bersihin/main/bersihin.py"
$Here = if ($MyInvocation.MyCommand.Path) { Split-Path -Parent $MyInvocation.MyCommand.Path } else { (Get-Location).Path }
$LocalSource = Join-Path $Here "bersihin.py"
$TempSource = $null

$Python = $null
if (Get-Command py -ErrorAction SilentlyContinue) { $Python = "py" }
elseif (Get-Command python -ErrorAction SilentlyContinue) { $Python = "python" }
if (-not $Python) { throw "Python 3.9+ belum terpasang / tidak ada di PATH." }

try {
    if (Test-Path $LocalSource) {
        $Source = $LocalSource
    } else {
        $TempSource = Join-Path $env:TEMP ("bersihin-" + [guid]::NewGuid().ToString("N") + ".py")
        Write-Host "[*] bersihin.py tidak ada di folder lokal; mengunduh dari GitHub..."
        Invoke-WebRequest -UseBasicParsing -Uri $RawSource -OutFile $TempSource
        & $Python -m py_compile $TempSource
        if ($LASTEXITCODE -ne 0) { throw "Source hasil download gagal validasi Python." }
        $Source = $TempSource
    }

    $InstallDir = Join-Path $env:LOCALAPPDATA "Bersihin"
    $BinDir = Join-Path $env:LOCALAPPDATA "Programs\Bersihin\bin"
    New-Item -ItemType Directory -Force -Path $InstallDir, $BinDir | Out-Null
    Copy-Item -Force $Source (Join-Path $InstallDir "bersihin.py")

    $Cmd = "@echo off`r`n$Python `"$InstallDir\bersihin.py`" %*`r`n"
    Set-Content -Encoding ASCII -Path (Join-Path $BinDir "bersihin.cmd") -Value $Cmd

    $UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $Parts = @($UserPath -split ';' | Where-Object { $_ })
    if ($Parts -notcontains $BinDir) {
        $NewPath = (($Parts + $BinDir) -join ';')
        [Environment]::SetEnvironmentVariable("Path", $NewPath, "User")
        $env:Path += ";$BinDir"
        Write-Host "[+] $BinDir ditambahkan ke User PATH. Buka terminal baru jika command belum terbaca."
    }

    Write-Host "[+] Bersihin terpasang di $InstallDir"
    Write-Host "[*] Cek platform: bersihin --doctor"
    Write-Host "[*] Scan aman:    bersihin --dry-run --verbose"
}
finally {
    if ($TempSource -and (Test-Path $TempSource)) { Remove-Item -Force $TempSource }
}
