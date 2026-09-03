; ==============================================================================
; FTODE Companion Host - Inno Setup 6 Script
; Generates FTODE-Host-Setup-Windows.exe with Windows Control Panel / Installed Apps integration
; ==============================================================================

#define MyAppName "FTODE Companion Host"
#define MyAppVersion "1.0.3"
#define MyAppPublisher "MaxAkt"
#define MyAppURL "https://github.com/Maximos2004/FTODE"

[Setup]
AppId={{C1A0D663-8F32-4E90-BA10-4A0B8497D7DE}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={localappdata}\FTODE
DisableDirPage=no
DefaultGroupName=FTODE
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=FTODE-Host-Setup-Windows
SetupIconFile=..\dist\ftode_logo.ico
UninstallDisplayIcon={app}\ftode_logo.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
LicenseFile=..\LICENSE

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "regchromium"; Description: "Chromium Browsers (Chrome, Opera, Opera GX, Edge, Brave, Vivaldi)"; GroupDescription: "Browser Integration:"
Name: "regfirefox"; Description: "Firefox && Firefox-based Browsers (Waterfox, LibreWolf, Floorp, Zen)"; GroupDescription: "Browser Integration:"
Name: "bootstrap"; Description: "Download and configure latest yt-dlp && FFmpeg during installation"; GroupDescription: "Media Tools:"

[Files]
Source: "..\native_host\host.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\native_host\run_host.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\ftode_logo.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion

[Registry]
; Chromium Browsers
Root: HKCU; Subkey: "Software\Google\Chrome\NativeMessagingHosts\com.ftode.host"; ValueType: string; ValueName: ""; ValueData: "{app}\com.ftode.host.json"; Flags: uninsdeletekey; Tasks: regchromium
Root: HKCU; Subkey: "Software\Microsoft\Edge\NativeMessagingHosts\com.ftode.host"; ValueType: string; ValueName: ""; ValueData: "{app}\com.ftode.host.json"; Flags: uninsdeletekey; Tasks: regchromium
Root: HKCU; Subkey: "Software\Opera Software\NativeMessagingHosts\com.ftode.host"; ValueType: string; ValueName: ""; ValueData: "{app}\com.ftode.host.json"; Flags: uninsdeletekey; Tasks: regchromium
Root: HKCU; Subkey: "Software\Opera Software\Opera GX\NativeMessagingHosts\com.ftode.host"; ValueType: string; ValueName: ""; ValueData: "{app}\com.ftode.host.json"; Flags: uninsdeletekey; Tasks: regchromium
Root: HKCU; Subkey: "Software\Opera Software\Opera Stable\NativeMessagingHosts\com.ftode.host"; ValueType: string; ValueName: ""; ValueData: "{app}\com.ftode.host.json"; Flags: uninsdeletekey; Tasks: regchromium

; Mozilla Firefox
Root: HKCU; Subkey: "Software\Mozilla\NativeMessagingHosts\com.ftode.host"; ValueType: string; ValueName: ""; ValueData: "{app}\com.ftode.host-firefox.json"; Flags: uninsdeletekey; Tasks: regfirefox

[Run]
; 1. Generate manifests & configure registries
Filename: "{cmd}"; Parameters: "/c ""{app}\run_host.bat"" --install"; Flags: runhidden; StatusMsg: "Configuring browser native messaging manifests..."
; 2. Bootstrap binaries if task is selected
Filename: "{cmd}"; Parameters: "/c ""{app}\run_host.bat"" --bootstrap"; Flags: runhidden; StatusMsg: "Downloading and configuring yt-dlp & FFmpeg binaries (please wait)..."; Tasks: bootstrap

[UninstallRun]
; Cleanly remove native messaging registry keys and manifests
Filename: "{cmd}"; Parameters: "/c ""{app}\run_host.bat"" --uninstall"; Flags: runhidden; RunOnceId: "FTODEHostUninstall"

[UninstallDelete]
Type: filesandordirs; Name: "{app}\bin"
Type: filesandordirs; Name: "{app}\__pycache__"
Type: files; Name: "{app}\debug_host.log*"
Type: files; Name: "{app}\com.ftode.host*.json"
Type: files; Name: "{app}\*.pyc"
