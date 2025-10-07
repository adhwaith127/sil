[Setup]
AppName=BiometricServer
AppVersion=1.0
DefaultDirName={autopf}\BiometricServer
DefaultGroupName=BiometricServer
UninstallDisplayIcon={app}\BiometricServer.exe
Compression=lzma2
SolidCompression=yes
OutputDir=installer
OutputBaseFilename=BiometricServer_Setup

[Files]
Source: "dist\BiometricServer.exe"; DestDir: "{app}"

[Icons]
Name: "{group}\BiometricServer"; Filename: "{app}\BiometricServer.exe"
Name: "{group}\Uninstall BiometricServer"; Filename: "{uninstallexe}"
Name: "{autodesktop}\BiometricServer"; Filename: "{app}\BiometricServer.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked

[Run]
Filename: "{app}\BiometricServer.exe"; Description: "Launch BiometricServer"; Flags: postinstall nowait skipifsilent
