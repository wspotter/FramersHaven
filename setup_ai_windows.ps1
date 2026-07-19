[CmdletBinding()]
param(
    [string]$Model = "hf.co/ggml-org/SmolVLM2-2.2B-Instruct-GGUF:Q4_K_M"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Find-OllamaExecutable {
    $command = Get-Command ollama -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }
    $candidate = Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"
    if (Test-Path $candidate) {
        return $candidate
    }
    return $null
}

function Test-OllamaServer {
    param([string]$Executable)
    & $Executable list *> $null
    return $LASTEXITCODE -eq 0
}

$ollama = Find-OllamaExecutable
if (-not $ollama) {
    Write-Host "Ollama is not installed. Running Ollama's official Windows installer..."
    $installer = Join-Path $env:TEMP "FramersHaven-Ollama-$PID.ps1"
    try {
        Invoke-WebRequest -UseBasicParsing -Uri "https://ollama.com/install.ps1" -OutFile $installer
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $installer
        if ($LASTEXITCODE -ne 0) {
            throw "The Ollama installer returned exit code $LASTEXITCODE."
        }
    } finally {
        Remove-Item -LiteralPath $installer -Force -ErrorAction SilentlyContinue
    }
    $ollama = Find-OllamaExecutable
}

if (-not $ollama) {
    throw "Ollama installed but its command is not available yet. Restart Windows, then run setup_ai_windows.ps1 again."
}

if (-not (Test-OllamaServer $ollama)) {
    Write-Host "Starting Ollama..."
    Start-Process -FilePath $ollama -ArgumentList "serve" -WindowStyle Hidden
    $ready = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        Start-Sleep -Seconds 1
        if (Test-OllamaServer $ollama) {
            $ready = $true
            break
        }
    }
    if (-not $ready) {
        throw "Ollama did not start. Start Ollama from the Windows Start menu, then run setup_ai_windows.ps1 again."
    }
}

Write-Host "Downloading the optional Framewise vision model. This can take several minutes..."
& $ollama pull $Model
if ($LASTEXITCODE -ne 0) {
    throw "The Framewise model download failed. Check the internet connection and run this script again."
}
& $ollama show $Model *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Ollama could not verify the downloaded Framewise model."
}

Write-Host ""
Write-Host "Framewise local AI is ready."
Write-Host "Open FramersHaven, go to Admin > Framewise, enable it, then Save and Test."
Write-Host "Provider: Ollama"
Write-Host "URL: http://127.0.0.1:11434/v1"
Write-Host "Model: $Model"
