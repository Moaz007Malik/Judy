#define MyAppName "Judy Executive Assistant"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "Judy"
#define MyAppExeName "Judy.exe"

[Setup]
AppId={{A9B5D8A4-8D42-4D1D-91C1-DA72F1450C8B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Judy
DefaultGroupName=Judy
OutputDir=..\dist\installer
OutputBaseFilename=JudySetup-{#MyAppVersion}
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=lowest
WizardStyle=modern
Compression=lzma2
SolidCompression=yes
UninstallDisplayIcon={app}\{#MyAppExeName}

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked
Name: "startup"; Description: "Launch Judy when I sign in to Windows"; GroupDescription: "Startup:"; Flags: unchecked

[Files]
Source: "..\dist\Judy\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Judy"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\Judy"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userstartup}\Judy"; Filename: "{app}\{#MyAppExeName}"; Tasks: startup

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Judy"; Flags: nowait postinstall skipifsilent
