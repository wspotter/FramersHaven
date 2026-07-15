from pathlib import Path


ROOT = Path(__file__).parent.parent
INSTALLER = ROOT / "install_windows.ps1"
LAUNCHER = ROOT / "run_windows.bat"
SHELL_LAUNCHER = ROOT / "scripts" / "run.sh"
WINDOWS_INSTALL_DOC = ROOT / "docs" / "WINDOWS_INSTALL.md"
START_HERE_WINDOWS = ROOT / "START_HERE_WINDOWS.txt"
POWERSHELL_INSTALL_COMMAND = (
    '$installer="$env:TEMP\\FramersHaven-install.ps1"; Invoke-WebRequest '
    'https://raw.githubusercontent.com/wspotter/FramersHaven/main/install_windows.ps1 '
    '-OutFile $installer; & ([scriptblock]::Create((Get-Content -Raw $installer)))'
)


def test_installer_uses_expected_per_user_location_and_python_package():
    script = INSTALLER.read_text(encoding="utf-8")
    assert '$env:LOCALAPPDATA' in script
    assert '"FramersHaven"' in script
    assert "Python.Python.3.12" in script
    assert "winget" in script
    assert "3, 11" in script


def test_installer_downloads_without_git_and_preserves_existing_install():
    script = INSTALLER.read_text(encoding="utf-8")
    assert "FramersHaven/archive/refs/heads/main.zip" in script
    assert "Invoke-WebRequest" in script
    assert "run_windows.bat" in script
    assert "already exists but is not a FramersHaven installation" in script
    assert "git clone" not in script.lower()
    assert "Remove-Item $InstallRoot" not in script


def test_installer_resolves_python_launcher_to_real_interpreter():
    script = INSTALLER.read_text(encoding="utf-8")
    assert 'print(sys.executable)' in script
    assert "$env:PYTHON_EXE = $python" in script


def test_installer_checks_the_default_python3_launcher_candidate():
    script = INSTALLER.read_text(encoding="utf-8")
    assert '[pscustomobject]@{ Executable = "py"; Arguments = @("-3") }' in script


def test_launcher_accepts_and_validates_installer_python():
    launcher = LAUNCHER.read_text(encoding="utf-8")
    assert "PYTHON_EXE" in launcher
    assert "sys.version_info >= (3, 11)" in launcher


def test_launcher_checks_fallback_detection_at_execution_time():
    launcher = LAUNCHER.read_text(encoding="utf-8")
    assert "if not errorlevel 1" in launcher
    assert "%ERRORLEVEL%" not in launcher


def test_launcher_rejects_an_existing_venv_older_than_python311():
    launcher = LAUNCHER.read_text(encoding="utf-8")
    existing_venv_guard = 'if exist "venv\\Scripts\\python.exe" ('
    assert existing_venv_guard in launcher
    guard_body = launcher.split(existing_venv_guard, 1)[1].split(
        'if not exist "venv\\Scripts\\python.exe" (', 1
    )[0]
    assert (
        '"venv\\Scripts\\python.exe" -c "import sys; raise SystemExit(0 if '
        'sys.version_info >= (3, 11) else 1)"'
    ) in guard_body
    assert "The existing virtual environment uses Python older than 3.11." in guard_body
    assert "Rename or remove the venv folder manually" in guard_body
    assert "exit /b 1" in guard_body


def test_readme_publishes_the_one_command_installer():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "raw.githubusercontent.com/wspotter/FramersHaven/main/install_windows.ps1" in readme
    assert "%LOCALAPPDATA%" in readme
    assert "127.0.0.1" in readme


def test_readme_documents_the_curated_catalog_preview_exception():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert (
        "`catalog_previews/` runtime content is ignored except the three curated "
        "fictional demo assets"
    ) in readme


def test_public_windows_docs_publish_the_same_exact_installer_command():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    windows_install = WINDOWS_INSTALL_DOC.read_text(encoding="utf-8")
    assert readme.count(POWERSHELL_INSTALL_COMMAND) == 1
    assert windows_install.count(POWERSHELL_INSTALL_COMMAND) == 1


def test_shell_launcher_defaults_to_localhost():
    launcher = SHELL_LAUNCHER.read_text(encoding="utf-8")
    assert 'HOST="${HOST:-127.0.0.1}"' in launcher


def test_public_windows_docs_do_not_include_future_publication_copy():
    public_docs = (ROOT / "README.md", WINDOWS_INSTALL_DOC, START_HERE_WINDOWS)
    for path in public_docs:
        contents = path.read_text(encoding="utf-8")
        assert "will become live after" not in contents.lower(), path
