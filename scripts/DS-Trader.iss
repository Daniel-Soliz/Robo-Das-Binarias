; Compilar com Inno Setup 6 em Windows x64 (scripts/build.ps1)
#define MyAppName "DS Trader"
#define MyAppVersion "1.4.0"
#define MyAppPublisher "DS Digital"
#define MyAppExeName "DS-Trader.exe"

[Setup]
AppId={{D50879D2-1CA5-4F80-A673-FCA6A62D24CA}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\DS Trader
DefaultGroupName=DS Trader
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
OutputDir=..\release-build
OutputBaseFilename=DS-Trader-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}
SetupLogging=yes
CloseApplications=yes

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Files]
Source: "..\dist\DS-Trader\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\examples\*"; DestDir: "{app}\Exemplos"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\docs\MANUAL.md"; DestDir: "{app}\Documentacao"; Flags: ignoreversion
Source: "..\docs\ESTRATEGIA.md"; DestDir: "{app}\Documentacao"; Flags: ignoreversion
Source: "..\docs\TESTES.md"; DestDir: "{app}\Documentacao"; Flags: ignoreversion

[Icons]
Name: "{userdesktop}\DS Trader"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Comment: "DS Trader — Análise e Simulação"
Name: "{autoprograms}\DS Trader"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir DS Trader"; Flags: nowait postinstall skipifsilent
