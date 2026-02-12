!include "MUI2.nsh"

; 基本信息
Name "Andless Console"
OutFile "AndlessConsole-Setup.exe"
InstallDir "$PROGRAMFILES\Andless Console"
InstallDirRegKey HKLM "Software\Andless Console" "Install_Dir"
RequestExecutionLevel admin

; 界面设置
!define MUI_ABORTWARNING

; 安装页面
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; 卸载页面
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; 语言
!insertmacro MUI_LANGUAGE "SimpChinese"

Section "Install"
    SetOutPath "$INSTDIR"

    ; 复制所有文件
    File /r "dist\console\*.*"

    ; 写入注册表
    WriteRegStr HKLM "Software\Andless Console" "Install_Dir" "$INSTDIR"

    ; 卸载信息
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AndlessConsole" "DisplayName" "Andless Console"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AndlessConsole" "UninstallString" '"$INSTDIR\uninstall.exe"'
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AndlessConsole" "InstallLocation" "$INSTDIR"
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AndlessConsole" "NoModify" 1
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AndlessConsole" "NoRepair" 1

    WriteUninstaller "$INSTDIR\uninstall.exe"

    ; 开始菜单快捷方式
    CreateDirectory "$SMPROGRAMS\Andless Console"
    CreateShortcut "$SMPROGRAMS\Andless Console\Andless Console.lnk" "$INSTDIR\console.exe"
    CreateShortcut "$SMPROGRAMS\Andless Console\Uninstall.lnk" "$INSTDIR\uninstall.exe"

    ; 桌面快捷方式
    CreateShortcut "$DESKTOP\Andless Console.lnk" "$INSTDIR\console.exe"
SectionEnd

Section "Uninstall"
    ; 删除注册表
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AndlessConsole"
    DeleteRegKey HKLM "Software\Andless Console"

    ; 删除快捷方式
    Delete "$SMPROGRAMS\Andless Console\*.lnk"
    RMDir "$SMPROGRAMS\Andless Console"
    Delete "$DESKTOP\Andless Console.lnk"

    ; 删除安装目录
    RMDir /r "$INSTDIR"
SectionEnd
