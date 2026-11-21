#ifndef Version
  #define Version "0.0.0"
#endif

#define Nom "Riftbound Collection"
#define Exe "RiftboundCollection.exe"
#define IdWindows "MiniZellsis.RiftboundCollection"

[Setup]
SourceDir=..
AppId={{E3B8DC2A-BE62-4C13-ADEB-CDBF71B58050}
AppName={#Nom}
AppVersion={#Version}
AppVerName={#Nom} {#Version}
AppPublisher=MiniZellsis
AppPublisherURL=https://github.com/MiniZellsis/riftbound-collection
AppUpdatesURL=https://github.com/MiniZellsis/riftbound-collection/releases
DefaultDirName={autopf}\{#Nom}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=dist
OutputBaseFilename=RiftboundCollection-Setup-{#Version}
SetupIconFile=ressources\icone.ico
UninstallDisplayIcon={app}\{#Exe}
UninstallDisplayName={#Nom}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "bureau"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[InstallDelete]
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "dist\RiftboundCollection\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#Nom}"; Filename: "{app}\{#Exe}"; AppUserModelID: "{#IdWindows}"
Name: "{autodesktop}\{#Nom}"; Filename: "{app}\{#Exe}"; Tasks: bureau; AppUserModelID: "{#IdWindows}"

[Run]
Filename: "{app}\{#Exe}"; Description: "{cm:LaunchProgram,{#Nom}}"; Flags: nowait postinstall skipifsilent
