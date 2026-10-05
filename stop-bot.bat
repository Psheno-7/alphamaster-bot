@echo off
schtasks /End /TN "AlphaMaster Bot" >nul 2>&1
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name like 'python%%'\" | Where-Object { $_.CommandLine -match 'alphamaster|autostart.pyw' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
echo AlphaMaster stopped.
pause
