from __future__ import annotations

import os
import subprocess
from pathlib import Path

from scripts import build_windows_package


ROOT = Path(__file__).parent.parent
MODEL = "hf.co/ggml-org/SmolVLM2-2.2B-Instruct-GGUF:Q4_K_M"
UNIX_INSTALL_COMMAND = (
    'installer="$(mktemp)"; curl -fsSL '
    "https://raw.githubusercontent.com/wspotter/FramersHaven/main/install.sh "
    '-o "$installer" && bash "$installer"; rm -f "$installer"'
)


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_unix_install_and_launch_scripts_exist_are_executable_and_parse() -> None:
    scripts = (
        "install.sh",
        "setup_ai.sh",
        "Start FramersHaven.command",
        "scripts/bootstrap_unix.sh",
        "scripts/run.sh",
    )
    for relative in scripts:
        path = ROOT / relative
        assert path.is_file(), relative
        assert os.access(path, os.X_OK), relative
        subprocess.run(["bash", "-n", str(path)], check=True)


def test_unix_installer_has_platform_specific_user_locations_and_no_git_requirement() -> None:
    script = read("install.sh")
    assert "Darwin" in script
    assert "Linux" in script
    assert "Applications/FramersHaven" in script
    assert ".local/share/FramersHaven" in script
    assert "FramersHaven/archive/refs/heads/main.tar.gz" in script
    assert "git clone" not in script.lower()
    assert "--no-launch" in script


def test_unix_bootstrap_detects_python_builds_a_venv_and_initializes_data() -> None:
    script = read("scripts/bootstrap_unix.sh")
    assert "sys.version_info >= (3, 11)" in script
    assert "python3.12" in script
    assert "python3.11" in script
    assert "-m venv" in script
    assert "UV_UNMANAGED_INSTALL" in script
    assert "venv --seed --python 3.12" in script
    assert "requirements.txt" in script
    assert "scripts/seed_demo.py" in script
    assert "studio.db" in script


def test_model_download_is_confined_to_explicit_ai_setup() -> None:
    ai_shell = read("setup_ai.sh")
    ai_windows = read("setup_ai_windows.ps1")
    assert MODEL in ai_shell
    assert MODEL in ai_windows
    assert 'pull "${MODEL}"' in ai_shell
    assert " pull $Model" in ai_windows

    for relative in ("install.sh", "scripts/bootstrap_unix.sh", "scripts/run.sh"):
        contents = read(relative)
        assert MODEL not in contents, relative
        assert "ollama pull" not in contents.lower(), relative


def test_readme_and_platform_docs_publish_the_supported_commands() -> None:
    readme = read("README.md")
    mac = read("docs/MAC_INSTALL.md")
    linux = read("docs/LINUX_INSTALL.md")
    ai = read("docs/AI_SETUP.md")

    assert readme.count(UNIX_INSTALL_COMMAND) == 1
    assert mac.count(UNIX_INSTALL_COMMAND) == 1
    assert linux.count(UNIX_INSTALL_COMMAND) == 1
    assert "docs/MAC_INSTALL.md" in readme
    assert "docs/LINUX_INSTALL.md" in readme
    assert "docs/AI_SETUP.md" in readme
    assert MODEL in ai


def test_public_install_docs_have_no_login_or_demo_account_instructions() -> None:
    public_install_docs = (
        "README.md",
        "START_HERE_WINDOWS.txt",
        "docs/WINDOWS_INSTALL.md",
        "docs/MAC_INSTALL.md",
        "docs/LINUX_INSTALL.md",
        "docs/AI_SETUP.md",
        "SECURITY.md",
    )
    forbidden = (
        "demo account",
        "default password",
        "sign in to framershaven",
        "log in to framershaven",
        "simple local login",
    )
    for relative in public_install_docs:
        contents = read(relative).lower()
        for phrase in forbidden:
            assert phrase not in contents, f"{phrase!r} in {relative}"


def test_browser_smoke_does_not_expect_removed_login_credentials() -> None:
    smoke = read("scripts/browser_smoke.py")
    assert "FRAMERSHAVEN_SMOKE_USERNAME" not in smoke
    assert "FRAMERSHAVEN_SMOKE_PASSWORD" not in smoke
    assert "input[name='username']" not in smoke
    assert 'name="Sign In"' not in smoke


def test_removed_login_module_is_not_distributed() -> None:
    assert not (ROOT / "app" / "auth.py").exists()


def test_install_docs_warn_against_public_internet_hosting() -> None:
    for relative in (
        "docs/WINDOWS_INSTALL.md",
        "docs/MAC_INSTALL.md",
        "docs/LINUX_INSTALL.md",
        "docs/AI_SETUP.md",
    ):
        contents = read(relative).lower()
        assert "trusted" in contents, relative
        assert "private lan" in contents, relative
        assert "public internet" in contents, relative


def test_cross_platform_entrypoints_are_in_the_windows_package_manifest() -> None:
    for relative in (
        "install.sh",
        "setup_ai.sh",
        "setup_ai_windows.ps1",
        "Start FramersHaven.command",
    ):
        assert relative in build_windows_package.INCLUDE_FILES
