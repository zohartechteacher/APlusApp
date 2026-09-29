; Inno Setup script for distributing the A+ Practice Exam desktop app.
; Build with: iscc installer.iss

#define MyAppName "APlus Practice Exam"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "APlus Practice Exam"
#define MyAppExeName "APlusPracticeExam.exe"

[Setup]
AppId={{E9D68679-F97F-4C28-B16E-31D52658CE6B}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\APlus Practice Exam
DefaultGroupName={#MyAppName}
OutputBaseFilename=setup_APlusPracticeExam
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\Zfav.ico
OutputDir={src}\Output
WizardStyle=modern
SetupIconFile=Zfav.ico

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "Zfav.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\Zfav.ico"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\Zfav.ico"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
