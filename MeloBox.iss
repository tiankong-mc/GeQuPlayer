; ==============================================================
;  GeQuPlayer 安装脚本 - Inno Setup 7.x
;  Author: tiankong
;  GitHub: https://github.com/tiankong-mc/GeQuPlayer
;
;  使用前：
;    1. 先用 PyInstaller 打包：python -m PyInstaller build.spec --noconfirm
;    2. 确认 dist\MusicPlayer\MusicPlayer.exe 存在
;    3. 确认 myicon.ico 在项目根目录
;    4. 确认 Inno Setup 语言包 ChineseSimplified.isl 已放到
;       C:\Program Files (x86)\Inno Setup 7\Languages\
; ==============================================================

[Setup]
; ---------- 基本信息 ----------
AppName=GeQuPlayer
AppVersion=1.2.3
AppVerName=GeQuPlayer 1.2.3
AppPublisher=tiankong
AppPublisherURL=https://github.com/tiankong-mc/GeQuPlayer
AppSupportURL=https://github.com/tiankong-mc/GeQuPlayer/issues
AppUpdatesURL=https://github.com/tiankong-mc/GeQuPlayer/releases
AppCopyright=Copyright (C) 2025 tiankong

; ---------- 安装目录 ----------
DefaultDirName={userdocs}\GeQuPlayer
DefaultGroupName=GeQuPlayer
DisableProgramGroupPage=yes
AllowNoIcons=yes

; ---------- 输出 ----------
OutputDir=installer_output
OutputBaseFilename=GeQuPlayer_Setup_v1.2.3
SetupIconFile=myicon.ico
UninstallDisplayIcon={app}\MusicPlayer.exe
UninstallDisplayName=GeQuPlayer
Compression=lzma2/fast
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

MinVersion=10.0

CreateUninstallRegKey=yes
Uninstallable=yes

; ==============================================================
;  中文界面
; ==============================================================
[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

; ==============================================================
;  打包文件
; ==============================================================
[Files]
Source: "dist\MusicPlayer\*"; DestDir: "{app}"; \
    Flags: ignoreversion recursesubdirs createallsubdirs

; ==============================================================
;  附加任务
; ==============================================================
[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; \
    GroupDescription: "附加任务："; Flags: unchecked

; ==============================================================
;  快捷方式
; ==============================================================
[Icons]
Name: "{group}\GeQuPlayer"; Filename: "{app}\MusicPlayer.exe"
Name: "{group}\卸载 GeQuPlayer"; Filename: "{uninstallexe}"
Name: "{autodesktop}\GeQuPlayer"; Filename: "{app}\MusicPlayer.exe"; \
    Tasks: desktopicon

; ==============================================================
;  安装完成后
; ==============================================================
[Run]
Filename: "{app}\MusicPlayer.exe"; \
    Description: "立即运行 GeQuPlayer"; \
    Flags: nowait postinstall skipifsilent

; ==============================================================
;  自定义页面：缓存目录 + 下载目录
; ==============================================================
[Code]
var
  ConfigPage: TInputDirWizardPage;

procedure InitializeWizard();
begin
  ConfigPage := CreateInputDirPage(wpSelectDir,
    '选择附加目录',
    '请选择缓存和下载目录的位置。',
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
    RegWriteStringValue(HKEY_CURRENT_USER, 'Software\GeQuPlayer',
      'InstallPath', ExpandConstant('{app}'));
    RegWriteStringValue(HKEY_CURRENT_USER, 'Software\GeQuPlayer',
      'CacheDir', GetCacheDir(''));
    RegWriteStringValue(HKEY_CURRENT_USER, 'Software\GeQuPlayer',
      'DownloadDir', GetDownloadDir(''));
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
  begin
    RegDeleteKeyIncludingSubkeys(HKEY_CURRENT_USER, 'Software\GeQuPlayer');
  end;
end;