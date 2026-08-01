param(
    [string]$Version = "0.0.0-dev",
    [string]$VersionInfoVersion = ""
)

$ErrorActionPreference = "Stop"
$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Push-Location $RepositoryRoot
try {
    if (-not $VersionInfoVersion) {
        $match = [regex]::Match($Version, '\d+(?:\.\d+){0,3}')
        if (-not $match.Success) {
            $VersionInfoVersion = "0.0.0.0"
        } else {
            $parts = @($match.Value.Split('.'))
            while ($parts.Count -lt 4) { $parts += "0" }
            $VersionInfoVersion = ($parts[0..3] -join '.')
        }
    }

    New-Item -ItemType Directory -Force -Path "build\windows" | Out-Null

    @'
from pathlib import Path
from PIL import Image

source = Path("app/static/logo.png")
target = Path("build/windows/FramersHaven.ico")
image = Image.open(source).convert("RGBA")
image.save(target, format="ICO", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
'@ | python -

    python -m PyInstaller --noconfirm --clean "packaging\windows\FramersHaven.spec"

    $CompilerCandidates = @(
        "${env:ProgramFiles}\Inno Setup 7\ISCC.exe",
        "${env:ProgramFiles(x86)}\Inno Setup 7\ISCC.exe",
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
    )
    $Compiler = $CompilerCandidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
    if (-not $Compiler) {
        throw "Inno Setup compiler was not found."
    }

    & $Compiler "/DMyAppVersion=$Version" "/DMyVersionInfoVersion=$VersionInfoVersion" "packaging\windows\FramersHaven.iss"
    if ($LASTEXITCODE -ne 0) {
        throw "Inno Setup failed with exit code $LASTEXITCODE."
    }

    $Installer = "dist\installer\FramersHaven-Setup.exe"
    if (-not (Test-Path $Installer)) {
        throw "Installer output was not created: $Installer"
    }
    Get-FileHash -Algorithm SHA256 $Installer |
        ForEach-Object { "$($_.Hash.ToLower())  FramersHaven-Setup.exe" } |
        Set-Content -Encoding ascii "dist\installer\FramersHaven-Setup.exe.sha256"
}
finally {
    Pop-Location
}
