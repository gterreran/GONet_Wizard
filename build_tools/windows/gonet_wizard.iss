; Inno Setup script for the GONet Wizard Windows desktop installer.
;
; This script expects a PyInstaller one-dir GUI build in:
;   dist\GONet Wizard\
;
; Build it directly with ISCC.exe or through build_installer.ps1.

#define MyAppName "GONet Wizard"
#define MyAppExeName "GONet Wizard.exe"
#define MyAppPublisher "GONet Wizard"
#define MyAppURL "https://github.com/gterreran/GONet_Wizard"

#ifndef AppVersion
#define AppVersion "0.0.0"
#endif

#ifndef AppFileVersion
#define AppFileVersion "0.0.0.0"
#endif

#ifndef SourceDir
#define SourceDir "..\..\dist\GONet Wizard"
#endif

#ifndef OutputDir
#define OutputDir "..\..\dist"
#endif

#ifndef OutputBaseFilename
#define OutputBaseFilename "GONet-Wizard-" + AppVersion + "-Windows-x64-unsigned-Setup"
#endif

[Setup]
AppId={{2AEE4DF7-8A7E-4DA4-9A92-BBA8C0320B34}
AppName={#MyAppName}
AppVersion={#AppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={localappdata}\Programs\GONet Wizard
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir={#OutputDir}
OutputBaseFilename={#OutputBaseFilename}
SetupIconFile=..\..\GONet_Wizard\static\img\logo\GONet_Wizard.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\{#MyAppExeName}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} installer
VersionInfoProductName={#MyAppName}
VersionInfoVersion={#AppFileVersion}
VersionInfoProductVersion={#AppFileVersion}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
