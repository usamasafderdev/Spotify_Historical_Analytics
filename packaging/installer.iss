#ifndef AppVersion
  #define AppVersion "0.1.8"
#endif
#ifndef PackageRoot
  #define PackageRoot "..\dist\USMusicChartsAnalytics"
#endif
#ifndef ReleaseOutput
  #define ReleaseOutput "..\dist\installer"
#endif

#ifndef AppName
  #define AppName "US Music Charts Analytics"
#endif
#ifndef AppIdentifier
  #define AppIdentifier "{{9A927D80-09E2-4E6A-9C79-B67D9C90DCA1}"
#endif
#ifndef OutputName
  #define OutputName "US-Music-Charts-Analytics-Setup"
#endif
#define AppExe "USMusicChartsAnalytics.exe"

[Setup]
AppId={#AppIdentifier}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppName}
AppPublisherURL=
DefaultDirName={localappdata}\Programs\US Music Charts Analytics
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir={#ReleaseOutput}
OutputBaseFilename={#OutputName}
SetupIconFile=..\assets\app_icon.ico
UninstallDisplayIcon={app}\{#AppExe}
Uninstallable=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
Compression=lzma2/fast
SolidCompression=yes
LZMANumBlockThreads=2
CloseApplications=yes
RestartApplications=no
UsePreviousAppDir=yes

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "{#PackageRoot}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "Launch {#AppName}"; Flags: postinstall nowait skipifsilent

[Code]
function RuntimeAvailable(FileName: String): Boolean;
var
  VersionMS, VersionLS: Cardinal;
begin
  Result := GetVersionNumbers(ExpandConstant('{sys}\') + FileName, VersionMS, VersionLS);
  if Result then
    Result := (VersionMS > $000E002C) or
      ((VersionMS = $000E002C) and (VersionLS >= $898B0000));
end;

function InitializeSetup(): Boolean;
begin
  Result := RuntimeAvailable('msvcp140.dll') and
    RuntimeAvailable('msvcp140_1.dll') and RuntimeAvailable('msvcp140_2.dll') and
    RuntimeAvailable('vcruntime140.dll') and RuntimeAvailable('vcruntime140_1.dll');
  if not Result then
    MsgBox('Microsoft Visual C++ v14 x64 runtime 14.44.35211.0 or newer is required.' + #13#10 +
      'Install it from https://aka.ms/vc14/vc_redist.x64.exe, then run Setup again.' + #13#10 +
      'Setup does not download or bundle Microsoft runtime DLLs.', mbError, MB_OK);
end;
