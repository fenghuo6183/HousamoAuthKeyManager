Add-Type -AssemblyName System.Drawing
$p = "D:\123\4\win\dist\AuthKeyManagerQt\AuthKeyManagerQt.exe"
$i = [System.Drawing.Icon]::ExtractAssociatedIcon($p)
$b = $i.ToBitmap()
$b.Save("D:\123\4\.tmp\exeicon.png")
Write-Output ("$($b.Width)x$($b.Height)")