$ErrorActionPreference = "SilentlyContinue"
$targets = Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -like "C:\AuthKeyManager\*" }
foreach ($p in $targets) {
  Write-Output ("kill " + $p.ProcessId + " " + $p.Name)
  Stop-Process -Id $p.ProcessId -Force
}
