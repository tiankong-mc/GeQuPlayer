; ==============================================================
;  GeQuPlayer 安装脚本 - Inno Setup 7.x
;  Author: tiankong
;  GitHub: https://github.com/tiankong-mc/GeQuPlayer
; ==============================================================

[Setup]
; ---------- 基本信息 ----------
AppName=GeQuPlayer
AppVersion=1.2.0
AppVerName=GeQuPlayer 1.2.0
AppPublisher=tiankong
AppPublisherURL=https://github.com/tiankong-mc/GeQuPlayer
AppSupportURL=https://github.com/tiankong-mc/GeQuPlayer/issues
AppUpdatesURL=https://github.com/tiankong-mc/GeQuPlayer/releases

; ---------- 安装目录 ----------
DefaultDirName={userdocs}\GeQuPlayer
DisableProgramGroupPage=yes

; ---------- 输出安装包 ----------
OutputDir=H:\音乐播放软件\安装包
OutputBaseFilename=GeQuPlayer_Setup
SetupIconFile=H:\音乐播放软件\myicon_1.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

; ---------- 权限与卸载 ----------
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\MusicPlayer.exe
UninstallDisplayName=GeQuPlayer

; ==============================================================
;  中文语言
; ==============================================================
[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

; ==============================================================
;  要打包的文件
; ==============================================================
[Files]
Source: "H:\音乐播放软件\dist\MusicPlayer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; ==============================================================
;  快捷方式
; ==============================================================
[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加任务："

[Icons]
Name: "{group}\GeQuPlayer"; Filename: "{app}\MusicPlayer.exe"
Name: "{group}\卸载 GeQuPlayer"; Filename: "{uninstallexe}"
Name: "{autodesktop}\GeQuPlayer"; Filename: "{app}\MusicPlayer.exe"; Tasks: desktopicon

; ==============================================================
;  安装完成后可以勾选"立即运行"
; ==============================================================
[Run]
Filename: "{app}\MusicPlayer.exe"; Description: "立即运行 GeQuPlayer"; Flags: nowait postinstall skipifsilent

; ==============================================================
;  自定义页面：选择缓存目录和下载目录
; ==============================================================
[Code]
var
  ConfigPage: TInputDirWizardPage;

procedure InitializeWizard();
begin
  ConfigPage := CreateInputDirPage(wpSelectDir,
    '选择附加目录', '请选择缓存和下载目录的位置。',
    '点击"下一步"继续，或点击"浏览"更改目录。',
    False, '');

  ConfigPage.Add('缓存目录（存放播放时产生的临时文件）：');
  ConfigPage.Add('下载目录（下载的音乐保存到这里）：');

  ConfigPage.Values[0] := ExpandConstant('{userdocs}\GeQuPlayer\Cache');
  ConfigPage.Values[1] := ExpandConstant('{userdocs}\GeQuPlayer\Downloads');
end;

function GetCacheDir(Param: String): String;
begin
  Result := ConfigPage.Values[0];
end;

function GetDownloadDir(Param: String): String;
begin
  Result := ConfigPage.Values[1];
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    RegWriteStringValue(HKEY_CURRENT_USER, 'Software\GeQuPlayer', 'InstallPath', ExpandConstant('{app}'));
    RegWriteStringValue(HKEY_CURRENT_USER, 'Software\GeQuPlayer', 'CacheDir', GetCacheDir(''));
    RegWriteStringValue(HKEY_CURRENT_USER, 'Software\GeQuPlayer', 'DownloadDir', GetDownloadDir(''));
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
  begin
    RegDeleteKeyIncludingSubkeys(HKEY_CURRENT_USER, 'Software\GeQuPlayer');
  end;
end;