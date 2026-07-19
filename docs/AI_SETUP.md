# Optional Local AI Setup

Framewise AI is optional. FramersHaven starts, designs frames, manages catalogs,
creates quotes, and produces catalog-grounded starter looks without Ollama or a
model. The basic installers do not download model weights.

## Recommended Model

The current local vision starter is:

```text
hf.co/ggml-org/SmolVLM2-2.2B-Instruct-GGUF:Q4_K_M
```

It is small enough for many current workstations, but image analysis can still
be slow on CPU-only hardware. Apple Silicon or a supported GPU provides a
better counter experience. Intel Macs can run the app and current Ollama builds
on macOS Sonoma or newer, but local model inference is CPU-only.

## Windows

After the basic install, open PowerShell and run:

```powershell
& "$env:LOCALAPPDATA\FramersHaven\setup_ai_windows.ps1"
```

## macOS

```bash
"$HOME/Applications/FramersHaven/setup_ai.sh"
```

## Linux

```bash
"$HOME/.local/share/FramersHaven/setup_ai.sh"
```

Running one of these scripts is the explicit opt-in. It detects Ollama, uses
Ollama's official installer when Ollama is missing, starts the local service,
and runs `ollama pull` for the recommended model. The download can take several
minutes. No AI package is required for basic FramersHaven use.

## Enable Framewise

After the setup script completes:

1. Start FramersHaven.
2. Open **Admin**, then **Framewise**.
3. Turn on **Enable Framewise**.
4. Confirm provider **Ollama** and URL `http://127.0.0.1:11434/v1`.
5. Confirm the recommended model name shown above.
6. Save the settings and use **Test provider**.

If the provider is unavailable later, FramersHaven keeps working and Framewise
falls back to local catalog-grounded starter looks.

## Troubleshooting

- Run `ollama list` to confirm the Ollama service and downloaded model are
  visible.
- If the service is stopped, start the Ollama app on Windows or macOS. On Linux,
  run `sudo systemctl start ollama` when installed as a system service.
- If the model download was interrupted, run the platform AI setup script
  again. Ollama resumes or verifies its local model files.
- If Framewise reports that the provider is unreachable, confirm the URL uses
  port 11434 and that another Ollama instance is not bound elsewhere.
- macOS Ollama currently requires macOS Sonoma 14 or newer. The basic
  FramersHaven app does not have that Ollama requirement.
- Antivirus, Gatekeeper, or endpoint security may inspect Ollama and model
  downloads. Verify the official `ollama.com` source rather than disabling
  security controls.

## Privacy and Network Boundary

With the default localhost URL, selected artwork and prompts stay on the same
workstation and are sent only to local Ollama. If an operator changes Framewise
to a LAN or cloud endpoint, that provider receives the submitted image and
prompt. Review that provider's privacy terms first.

Keep FramersHaven and Ollama on a trusted workstation or trusted private LAN.
Do not expose either service directly to the public internet.
