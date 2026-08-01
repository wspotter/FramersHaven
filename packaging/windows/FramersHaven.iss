#ifndef MyAppVersion
  #define MyAppVersion "0.0.0-dev"
#endif

#define MyAppName "FramersHaven"
#define MyAppExeName "FramersHaven.exe"

[Setup]
AppId={{89E72018-0A53-4E21-9A03-FBF42C00D9AF}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher=FramersHaven
AppPublisherURL=https://github.com/wspotter/FramersHaven
AppSupportURL=https://github.com/wspotter/FramersHaven/issues
AppUpdatesURL=https://github.com/wspotter/FramersHaven/releases
DefaultDirName={localappdata}\Programs\FramersHaven
DefaultGroupName=FramersHaven
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\..\dist\installer
OutputBaseFilename=FramersHaven-Setup
SetupIconFile=..\..\build\windows\FramersHaven.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
ArchitecturesAllowed=x64compatible
SetupArchitecture=x64
MinVersion=10.0
VersionInfoVersion={#MyAppVersion}
VersionInfoProductName={#MyAppName}
VersionInfoDescription=FramersHaven local framing workstation

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "..\..\dist\FramersHaven\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\FramersHaven"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\FramersHaven"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch FramersHaven"; Flags: nowait postinstall skipifsilent
