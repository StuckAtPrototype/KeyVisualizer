; KeyVisualizer Inno Setup Script
; Creates a Windows installer for KeyVisualizer

#define MyAppName "KeyVisualizer"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "StuckAtPrototype"
#define MyAppURL "https://github.com/stuckatprototype/keyvisualizer"
#define MyAppExeName "KeyVisualizer.exe"

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
AppId={{B7F8C9D1-E4A3-4B2C-9F6D-8E5A1C3B7D9F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=LICENSE
OutputDir=installer_output
OutputBaseFilename=KeyVisualizer_Setup_v{#MyAppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
; SetupIconFile=keyvisualizer.ico  ; Uncomment when keyvisualizer.ico is in this folder
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
VersionInfoVersion={#MyAppVersion}
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startup"; Description: "Launch at Windows startup"; GroupDescription: "Startup Options:"; Flags: unchecked

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startup

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; Kill the app if it's running before uninstall
Filename: "taskkill"; Parameters: "/F /IM {#MyAppExeName}"; Flags: runhidden; RunOnceId: "KillKeyVisualizer"

[Code]
function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
  AppRunning: Boolean;
begin
  Result := True;
  // Check if app is already running
  AppRunning := False;
  if Exec('tasklist', '/FI "IMAGENAME eq {#MyAppExeName}"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    if ResultCode = 0 then
    begin
      if MsgBox('KeyVisualizer is currently running. Do you want to close it and continue with the installation?', 
                mbConfirmation, MB_YESNO) = IDYES then
      begin
        Exec('taskkill', '/F /IM {#MyAppExeName}', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
        Sleep(1000);
      end
      else
      begin
        Result := False;
      end;
    end;
  end;
end;

function InitializeUninstall(): Boolean;
var
  ResultCode: Integer;
begin
  Result := True;
  // Try to close the app gracefully, then force kill if needed
  Exec('taskkill', '/IM {#MyAppExeName}', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Sleep(500);
  Exec('taskkill', '/F /IM {#MyAppExeName}', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Sleep(1000);
end;
