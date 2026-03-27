#define AppName "E舞成名重构版"
#define AppPublisher "liang"
#define AppExeName "E5CM-CG.exe"

#ifndef AppVersion
  #expr Error("未传入 AppVersion。请使用 2.打包成安装包.bat，或在 ISCC 中传入 /DAppVersion=2.0.0")
#endif

[Setup]
AppId={{9E0B6D5E-6A56-4D7B-BE4C-1F6B2C8A9E11}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultGroupName={#AppName}
AllowNoIcons=yes
OutputDir=installer_output
OutputBaseFilename=E5CM-CG_Setup_{#AppVersion}
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

[Dirs]
Name: "{app}\songs"
Name: "{app}\songs\diy"
Name: "{app}\songs\花式"
Name: "{app}\songs\竞速"
Name: "{app}\state"
Name: "{app}\userdata"
Name: "{app}\userdata\profile"
Name: "{app}\userdata\profile\avatars"

[InstallDelete]
Type: filesandordirs; Name: "{app}\backmovies"

[Files]
Source: "编译结果\E5CM-CG\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "编译结果\E5CM-CG\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "编译结果\E5CM-CG\backmovies\*"; DestDir: "{app}\backmovies"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "编译结果\E5CM-CG\config\*"; DestDir: "{app}\config"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "编译结果\E5CM-CG\core\*"; DestDir: "{app}\core"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "编译结果\E5CM-CG\scenes\*"; DestDir: "{app}\scenes"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "编译结果\E5CM-CG\songs\*"; DestDir: "{app}\songs"; Flags: ignoreversion recursesubdirs createallsubdirs; Check: ShouldInstallSongs
Source: "编译结果\E5CM-CG\state\runtime_state.sqlite3"; DestDir: "{app}\state"; Flags: ignoreversion skipifsourcedoesntexist; Check: ShouldInstallRuntimeStateDb
Source: "编译结果\E5CM-CG\userdata\*"; DestDir: "{app}\userdata"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist; Check: ShouldInstallUserData
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
var
  TargetStateReady: Boolean;
  TargetHasSongsDir: Boolean;
  TargetHasRuntimeStateDb: Boolean;
  TargetHasUserDataContent: Boolean;

function DirectoryHasEntries(const DirPath: String): Boolean;
var
  FindRec: TFindRec;
begin
  Result := False;
  if not DirExists(DirPath) then
    exit;

  if FindFirst(AddBackslash(DirPath) + '*', FindRec) then
  begin
    try
      repeat
        if (FindRec.Name <> '.') and (FindRec.Name <> '..') then
        begin
          Result := True;
          break;
        end;
      until not FindNext(FindRec);
    finally
      FindClose(FindRec);
    end;
  end;
end;

procedure SnapshotTargetInstallState(const AppDir: String);
var
  BaseDir: String;
begin
  BaseDir := Trim(AppDir);
  if BaseDir = '' then
    exit;

  TargetHasSongsDir := DirExists(AddBackslash(BaseDir) + 'songs');
  TargetHasRuntimeStateDb := FileExists(AddBackslash(BaseDir) + 'state\runtime_state.sqlite3');
  TargetHasUserDataContent := DirectoryHasEntries(AddBackslash(BaseDir) + 'userdata');
  TargetStateReady := True;
end;

procedure EnsureTargetStateSnapshot();
begin
  if not TargetStateReady then
    SnapshotTargetInstallState(ExpandConstant('{app}'));
end;

function ShouldInstallSongs(): Boolean;
begin
  EnsureTargetStateSnapshot();
  Result := not TargetHasSongsDir;
end;

function ShouldInstallRuntimeStateDb(): Boolean;
begin
  EnsureTargetStateSnapshot();
  Result := not TargetHasRuntimeStateDb;
end;

function ShouldInstallUserData(): Boolean;
begin
  EnsureTargetStateSnapshot();
  Result := not TargetHasUserDataContent;
end;

procedure CopyFileIfMissing(const SourcePath, TargetPath: String);
begin
  if (SourcePath = '') or (TargetPath = '') then
    exit;
  if (not FileExists(SourcePath)) or FileExists(TargetPath) then
    exit;

  ForceDirectories(ExtractFileDir(TargetPath));
  if RenameFile(SourcePath, TargetPath) then
    exit;

  CopyFile(SourcePath, TargetPath, False);
end;

procedure CopyDirContentsIfMissing(const SourceDir, TargetDir: String);
var
  FindRec: TFindRec;
  SourceItem: String;
  TargetItem: String;
  IsDirectory: Boolean;
begin
  if (SourceDir = '') or (TargetDir = '') then
    exit;
  if not DirExists(SourceDir) then
    exit;

  ForceDirectories(TargetDir);

  if FindFirst(AddBackslash(SourceDir) + '*', FindRec) then
  begin
    try
      repeat
        if (FindRec.Name <> '.') and (FindRec.Name <> '..') then
        begin
          SourceItem := AddBackslash(SourceDir) + FindRec.Name;
          TargetItem := AddBackslash(TargetDir) + FindRec.Name;
          IsDirectory := (FindRec.Attributes and FILE_ATTRIBUTE_DIRECTORY) <> 0;

          if IsDirectory then
            CopyDirContentsIfMissing(SourceItem, TargetItem)
          else if not FileExists(TargetItem) then
          begin
            ForceDirectories(ExtractFileDir(TargetItem));
            CopyFile(SourceItem, TargetItem, False);
          end;
        end;
      until not FindNext(FindRec);
    finally
      FindClose(FindRec);
    end;
  end;
end;

procedure MigrateLegacyUserData();
var
  AppDir: String;
  LegacyJsonDir: String;
  ProfileDir: String;
  AvatarDir: String;
  StateDir: String;
begin
  AppDir := ExpandConstant('{app}');
  LegacyJsonDir := AddBackslash(AppDir) + 'json';
  ProfileDir := AddBackslash(AppDir) + 'userdata\profile';
  AvatarDir := AddBackslash(ProfileDir) + 'avatars';
  StateDir := AddBackslash(AppDir) + 'state';

  ForceDirectories(AvatarDir);
  ForceDirectories(StateDir);

  CopyFileIfMissing(
    AddBackslash(LegacyJsonDir) + '个人资料.json',
    AddBackslash(ProfileDir) + '个人资料.json'
  );
  CopyFileIfMissing(
    AddBackslash(LegacyJsonDir) + 'runtime_state.sqlite3',
    AddBackslash(StateDir) + 'runtime_state.sqlite3'
  );
  CopyDirContentsIfMissing(
    AddBackslash(LegacyJsonDir) + '个人资料',
    AvatarDir
  );
end;

procedure EnsureSongsSkeletonFromManifest();
var
  SongsRoot: String;
  ManifestPath: String;
  ManifestLines: TArrayOfString;
  LineText: String;
  I: Integer;
begin
  SongsRoot := ExpandConstant('{app}\songs');
  ForceDirectories(SongsRoot);
  ForceDirectories(AddBackslash(SongsRoot) + 'diy');
  ManifestPath := AddBackslash(SongsRoot) + '_目录骨架清单.txt';

  if not FileExists(ManifestPath) then
    exit;
  if not LoadStringsFromFile(ManifestPath, ManifestLines) then
    exit;

  for I := 0 to GetArrayLength(ManifestLines) - 1 do
  begin
    LineText := Trim(ManifestLines[I]);
    if (LineText <> '') and (Pos('..', LineText) = 0) then
    begin
      StringChangeEx(LineText, '/', '\', True);
      if (Length(LineText) = 0) or ((LineText[1] <> '\') and (LineText[1] <> '/')) then
        ForceDirectories(AddBackslash(SongsRoot) + LineText);
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssInstall then
    SnapshotTargetInstallState(ExpandConstant('{app}'))
  else if CurStep = ssPostInstall then
  begin
    MigrateLegacyUserData();
    EnsureSongsSkeletonFromManifest();
  end;
end;
