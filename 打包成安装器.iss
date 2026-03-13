#define AppName "E舞成名重构版"
#define AppPublisher "liang"
#define AppExeName "E5CM-CG.exe"
#define Versionfilepath AddBackslash(SourcePath) + "json\客户端版本.json"
#define AppVersion Trim(ExecAndGetFirstLine( \
  "powershell.exe", \
  "-NoProfile -ExecutionPolicy Bypass -Command ""$ErrorActionPreference='Stop'; [Console]::OutputEncoding=[System.Text.Encoding]::UTF8; (Get-Content -Raw -LiteralPath '" + Versionfilepath + "' | ConvertFrom-Json).version""", \
  SourcePath \
))

#if AppVersion == ""
  #expr Error("读取 json\\客户端版本.json 失败，version 为空。")
#endif

[Setup]
AppId={{9E0B6D5E-6A56-4D7B-BE4C-1F6B2C8A9E11}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultGroupName={#AppName}
AllowNoIcons=yes
OutputDir=installer_output
OutputBaseFilename=E5CM-CG_Setup
SetupIconFile=icon\自解压安装器.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#AppExeName}
DefaultDirName={userdocs}\{#AppName}
PrivilegesRequired=lowest

[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"

[Files]
Source: "编译结果\E5CM-CG\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "编译结果\E5CM-CG\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "编译结果\E5CM-CG\backmovies\*"; DestDir: "{app}\backmovies"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "编译结果\E5CM-CG\core\*"; DestDir: "{app}\core"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "编译结果\E5CM-CG\json\*"; DestDir: "{app}\json"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "编译结果\E5CM-CG\scenes\*"; DestDir: "{app}\scenes"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "编译结果\E5CM-CG\songs\*"; DestDir: "{app}\songs"; Flags: ignoreversion recursesubdirs createallsubdirs; Check: ShouldInstallBundledSongs
Source: "编译结果\E5CM-CG\ui\*"; DestDir: "{app}\ui"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "编译结果\E5CM-CG\UI-img\*"; DestDir: "{app}\UI-img"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "编译结果\E5CM-CG\冷资源\*"; DestDir: "{app}\冷资源"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "编译结果\E5CM-CG\启动说明.txt"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\卸载 {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "立即启动 {#AppName}"; Flags: nowait postinstall skipifsilent

[Code]
function ShouldInstallBundledSongs(): Boolean;
begin
  Result := not DirExists(ExpandConstant('{app}\songs'));
end;
