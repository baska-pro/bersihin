$ErrorActionPreference = "Stop"
$RawSource = "https://raw.githubusercontent.com/baska-pro/bersihin/main/bersihin.py"
$TempSource = $null
$Source = $null

$PythonExe = $null
$PythonArgs = @()
$PyLauncher = Get-Command py -ErrorAction SilentlyContinue
$PythonCmd = Get-Command python -ErrorAction SilentlyContinue
if ($PyLauncher) { $PythonExe = $PyLauncher.Source; $PythonArgs = @("-3") }
elseif ($PythonCmd) { $PythonExe = $PythonCmd.Source }
if (-not $PythonExe) { throw "Python 3.9+ belum terpasang / tidak ada di PATH." }

& $PythonExe @PythonArgs -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)"
if ($LASTEXITCODE -ne 0) {
    $Detected = (& $PythonExe @PythonArgs --version 2>&1 | Out-String).Trim()
    throw "Dibutuhkan Python 3.9+; ditemukan: $Detected"
}

try {
    if ($env:BERSIHIN_SOURCE) {
        if (-not (Test-Path -LiteralPath $env:BERSIHIN_SOURCE -PathType Leaf)) { throw "BERSIHIN_SOURCE tidak ditemukan: $env:BERSIHIN_SOURCE" }
        $Source = (Resolve-Path -LiteralPath $env:BERSIHIN_SOURCE).Path
    }
    elseif ($MyInvocation.MyCommand.Path) {
        $Here = Split-Path -Parent $MyInvocation.MyCommand.Path
        $LocalSource = Join-Path $Here "bersihin.py"
        if (Test-Path -LiteralPath $LocalSource -PathType Leaf) { $Source = $LocalSource }
    }

    if (-not $Source) {
        $TempSource = Join-Path $env:TEMP ("bersihin-" + [guid]::NewGuid().ToString("N") + ".py")
        Write-Host "[*] Mengunduh bersihin.py dari GitHub..."
        Invoke-WebRequest -UseBasicParsing -Uri $RawSource -OutFile $TempSource
        $Source = $TempSource
    }

    & $PythonExe @PythonArgs -m py_compile $Source
    if ($LASTEXITCODE -ne 0) { throw "Source Bersihin gagal validasi Python." }

    $InstallDir = Join-Path $env:LOCALAPPDATA "Bersihin"
    $BinDir = Join-Path $env:LOCALAPPDATA "Programs\Bersihin\bin"
    $InstalledSource = Join-Path $InstallDir "bersihin.py"
    $InstalledCommand = Join-Path $BinDir "bersihin.cmd"
    New-Item -ItemType Directory -Force -Path $InstallDir, $BinDir | Out-Null

    $InstallTmp = Join-Path $InstallDir (".bersihin.py.tmp." + $PID)
    Copy-Item -Force -LiteralPath $Source -Destination $InstallTmp
    Move-Item -Force -LiteralPath $InstallTmp -Destination $InstalledSource

    $PythonPrefix = '"' + $PythonExe + '"'
    if ($PythonArgs.Count -gt 0) { $PythonPrefix += " " + ($PythonArgs -join " ") }
    $WrapperTmp = Join-Path $BinDir (".bersihin.cmd.tmp." + $PID)
    $Cmd = "@echo off`r`n$PythonPrefix `"$InstalledSource`" %*`r`n"
    Set-Content -Encoding ASCII -LiteralPath $WrapperTmp -Value $Cmd
    Move-Item -Force -LiteralPath $WrapperTmp -Destination $InstalledCommand

    $UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $Parts = @($UserPath -split ';' | Where-Object { $_ })
    if ($Parts -notcontains $BinDir) {
        [Environment]::SetEnvironmentVariable("Path", (($Parts + $BinDir) -join ';'), "User")
        $env:Path += ";$BinDir"
        Write-Host "[+] $BinDir ditambahkan ke User PATH."
    }

    Write-Host "[+] Bersihin terpasang di $InstallDir"
    Write-Host "[+] Command: $InstalledCommand"
    Write-Host "[*] Verifikasi instalasi..."
    & $InstalledCommand --version
    if ($LASTEXITCODE -ne 0) { throw "Verifikasi command Bersihin gagal." }
    Write-Host "[*] Cek platform: bersihin --doctor"
    Write-Host "[*] Scan aman:    bersihin --dry-run"
}
finally {
    if ($TempSource -and (Test-Path -LiteralPath $TempSource)) { Remove-Item -Force -LiteralPath $TempSource }
}
