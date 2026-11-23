param($name, $h = 1350)
# Rendert grafik\<name>.html mit Chrome (headless) nach grafik\<name>.png
$c = "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
if (-not (Test-Path $c)) { $c = "$env:ProgramFiles\Google\Chrome\Application\chrome.exe" }
$d = $PSScriptRoot
$url = "file:///" + ($d -replace '\\','/') + "/$name.html"
Start-Process -FilePath $c -ArgumentList "--headless=new","--disable-gpu","--hide-scrollbars","--force-device-scale-factor=1","--user-data-dir=$env:TEMP\chr_hl","--window-size=1080,$h","--screenshot=$d\$name.png",$url -Wait -RedirectStandardError "$env:TEMP\chr_err.txt"
