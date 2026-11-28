Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -like 'C:\AuthKeyManager*' } | Select-Object ProcessId,Name,ExecutablePath | Format-Table -AutoSize | Out-String -Width 300
