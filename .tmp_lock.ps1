$ErrorActionPreference = "SilentlyContinue"
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*AuthKeyManager*" -or $_.ExecutablePath -like "*AuthKeyManager*" } | Select-Object ProcessId, Name, ExecutablePath, CommandLine | Format-List
"----dirs----"
Get-ChildItem C:\ -Directory -Filter "AuthKeyManager*" | Select-Object Name, LastWriteTime
