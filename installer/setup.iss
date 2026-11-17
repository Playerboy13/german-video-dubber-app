; Inno Setup Script - German Video Dubber
; Baut einen einzigen Installer (.exe), der die gesamte App installiert.
; Der Nutzer muss danach nichts weiter installieren.

#define MyAppName "Deutscher Video-Synchronisierer"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "German Video Dubber"
#define MyAppExeName "GermanVideoDubber.exe"

[Setup]
AppId={{B6E2C9E4-7B9B-4C9E-9B7B-2C6E4B9E2C9F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=output
OutputBaseFilename=GermanVideoDubber-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
SetupLogging=yes

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "Verknüpfung auf dem Desktop erstellen"; GroupDescription: "Zusätzliche Symbole:"

[Files]
Source: "..\app\dist\GermanVideoDubber\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{#MyAppName} jetzt starten"; Flags: nowait postinstall skipifsilent
