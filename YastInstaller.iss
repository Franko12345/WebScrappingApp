[Setup]
AppName=Yast
AppVersion=1.0
DefaultDirName={autopf}\Yast
DefaultGroupName=Yast
OutputDir=.
OutputBaseFilename=YastInstaller
Compression=lzma
SolidCompression=yes
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes

[Tasks]
Name: "desktopicon"; Description: "Create Desktop Shortcut"; GroupDescription: "Additional icons:";

[Icons]
Name: "{group}\Yast"; Filename: "{app}\main.exe"
Name: "{commondesktop}\Yast"; Filename: "{app}\main.exe"; Tasks: desktopicon

[Registry]
Root: HKLM; Subkey: "SYSTEM\CurrentControlSet\Control\Session Manager\Environment"; \
    ValueType: string; ValueName: "BRAVE_PATH"; \
    ValueData: "{app}\brave\brave.exe"; Flags: preservestringtype

Root: HKLM; Subkey: "SYSTEM\CurrentControlSet\Control\Session Manager\Environment"; \
    ValueType: string; ValueName: "CHROMEDRIVER_PATH"; \
    ValueData: "{app}\chromedriver\chromedriver-win64\chromedriver.exe"; Flags: preservestringtype

[Code]

const
  REPO_URL   = 'https://github.com/Franko12345/WebScrappingApp.git';
  GIT_URL    = 'https://github.com/git-for-windows/git/releases/download/v2.45.2.windows.1/Git-2.45.2-64-bit.exe';
  PYTHON_URL = 'https://www.python.org/ftp/python/3.12.6/python-3.12.6-amd64.exe';
  BRAVE_URL  = 'https://github.com/brave/brave-browser/releases/download/v1.76.82/brave-v1.76.82-win32-x64.zip';

function IsGitInstalled(): Boolean;
var
  ResultCode: Integer;
begin
  Result := Exec('cmd.exe', '/c git --version', '', SW_HIDE, ewWaitUntilTerminated, ResultCode)
            and (ResultCode = 0);
end;

function IsPythonInstalled(): Boolean;
var
  ResultCode: Integer;
begin
  Result := Exec('cmd.exe', '/c python --version', '', SW_HIDE, ewWaitUntilTerminated, ResultCode)
            and (ResultCode = 0);
end;

procedure DownloadToTemp(const URL, FileName: string; var FullPath: string);
begin
  FullPath := ExpandConstant('{tmp}\' + FileName);
  DownloadTemporaryFile(URL, FileName, '', nil);
end;

procedure EnsureGit();
var
  InstallerPath: string;
  ResultCode: Integer;
begin
  if not IsGitInstalled() then
  begin
    MsgBox('Git not found. Downloading...', mbInformation, MB_OK);

    DownloadToTemp(GIT_URL, 'git-installer.exe', InstallerPath);

    if not Exec(InstallerPath, '/VERYSILENT /NORESTART', '', SW_HIDE,
      ewWaitUntilTerminated, ResultCode) then
      RaiseException('Failed to launch Git installer.');
  end;
end;

procedure EnsurePython();
var
  InstallerPath: string;
  ResultCode: Integer;
begin
  if not IsPythonInstalled() then
  begin
    MsgBox('Python not found. Downloading...', mbInformation, MB_OK);

    DownloadToTemp(PYTHON_URL, 'python-installer.exe', InstallerPath);

    if not Exec(InstallerPath,
      '/quiet InstallAllUsers=1 PrependPath=1 Include_test=0',
      '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
      RaiseException('Failed to launch Python installer.');
  end;
end;

procedure CloneRepo();
var
  ResultCode: Integer;
  AppDir: string;
begin
  AppDir := ExpandConstant('{app}');

  if DirExists(AppDir) then
    DelTree(AppDir, True, True, True);

  ForceDirectories(AppDir);

  if not Exec('cmd.exe',
    '/c git clone ' + REPO_URL + ' "' + AppDir + '"',
    '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
    RaiseException('Failed to clone repository.');
end;

procedure InstallRequirements();
var
  ResultCode: Integer;
  ReqPath: string;
begin
  ReqPath := ExpandConstant('{app}\requirements.txt');

  if FileExists(ReqPath) then
  begin
    if not Exec('cmd.exe',
      '/c python -m pip install -r "' + ReqPath + '"',
      '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
      RaiseException('Failed to install Python requirements.');
  end;
end;

procedure InstallBrave();
var
  ZipPath: string;
  ResultCode: Integer;
  BraveDir: string;
begin
  BraveDir := ExpandConstant('{app}\brave');

  if not DirExists(BraveDir) then
  begin
    MsgBox('Downloading Brave browser...', mbInformation, MB_OK);

    DownloadToTemp(BRAVE_URL, 'brave.zip', ZipPath);

    ForceDirectories(BraveDir);

    if not Exec('powershell.exe',
      '-Command "Expand-Archive -Path ''' + ZipPath +
      ''' -DestinationPath ''' + BraveDir + ''' -Force"',
      '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
      RaiseException('Failed to extract Brave.');
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssInstall then
  begin
    EnsureGit();
    EnsurePython();
    CloneRepo();
    InstallRequirements();
    InstallBrave();
  end;
end;