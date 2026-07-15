[CmdletBinding()]
param(
    [string]$InstallRoot = (Join-Path $env:LOCALAPPDATA "FramersHaven"),
    [switch]$NoLaunch
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$ArchiveUrl = "https://github.com/wspotter/FramersHaven/archive/refs/heads/main.zip"

function Test-Python311 {
    param([string]$Executable, [string[]]$PrefixArguments = @())
    if (-not (Test-Path $Executable) -and -not (Get-Command $Executable -ErrorAction SilentlyContinue)) {
        return $false
    }
    & $Executable @PrefixArguments -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" 2>$null
    return $LASTEXITCODE -eq 0
}

function Resolve-PythonExecutable {
    param([string]$Executable, [string[]]$PrefixArguments = @())
    $output = @(& $Executable @PrefixArguments -c "import sys; print(sys.executable)" 2>$null)
    if ($LASTEXITCODE -ne 0 -or $output.Count -eq 0) {
        return $null
    }
    return ([string]$output[-1]).Trim()
}

function Find-CompatiblePython {
    $candidates = @(
        [pscustomobject]@{ Executable = "py"; Arguments = @("-3") },
        [pscustomobject]@{ Executable = "py"; Arguments = @("-3.12") },
        [pscustomobject]@{ Executable = "py"; Arguments = @("-3.11") },
        [pscustomobject]@{ Executable = "python"; Arguments = @() },
        [pscustomobject]@{ Executable = (Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"); Arguments = @() },
        [pscustomobject]@{ Executable = (Join-Path $env:LOCALAPPDATA "Programs\Python\Python311\python.exe"); Arguments = @() }
    )
    foreach ($candidate in $candidates) {
        if (Test-Python311 $candidate.Executable $candidate.Arguments) {
            return Resolve-PythonExecutable $candidate.Executable $candidate.Arguments
        }
    }
    return $null
}

function Install-Python312 {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw "Python 3.11+ is missing and Windows Package Manager (winget) is unavailable. Install Python from https://www.python.org/downloads/windows/ and run this command again."
    }
    Write-Host "Python 3.11 or newer was not found. Installing Python 3.12 for this Windows user..."
    & winget install --exact --id Python.Python.3.12 --source winget --scope user --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) {
        throw "Python installation failed. Install Python 3.12 from https://www.python.org/downloads/windows/ and run this command again."
    }
}

$python = Find-CompatiblePython
if (-not $python) {
    Install-Python312
    $python = Find-CompatiblePython
}
if (-not $python) {
    throw "Python was installed but could not be detected. Close PowerShell, open it again, and rerun the install command."
}

$launcher = Join-Path $InstallRoot "run_windows.bat"
if (Test-Path $InstallRoot) {
    if (-not (Test-Path $launcher)) {
        throw "The destination already exists but is not a FramersHaven installation: $InstallRoot"
    }
    Write-Host "Using the existing FramersHaven installation at $InstallRoot"
} else {
    $parent = Split-Path $InstallRoot -Parent
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
    $archive = Join-Path $env:TEMP "FramersHaven-$PID.zip"
    $extract = Join-Path $parent ".FramersHaven-installing-$PID"
    try {
        Invoke-WebRequest -UseBasicParsing -Uri $ArchiveUrl -OutFile $archive
        Expand-Archive -LiteralPath $archive -DestinationPath $extract
        $source = Join-Path $extract "FramersHaven-main"
        if (-not (Test-Path (Join-Path $source "run_windows.bat"))) {
            throw "The downloaded FramersHaven archive has an unexpected layout."
        }
        Move-Item -LiteralPath $source -Destination $InstallRoot
    } finally {
        Remove-Item -LiteralPath $archive -Force -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $extract -Recurse -Force -ErrorAction SilentlyContinue
    }
}

if (-not $NoLaunch) {
    $env:PYTHON_EXE = $python
    Write-Host "Starting FramersHaven from $InstallRoot"
    & $launcher
} else {
    Write-Host "FramersHaven installed at $InstallRoot"
}
