# Max's Downloader - PowerShell Native Messaging Host Installer
param (
    [string]$ExtensionId = "iabbelaamkcbkklcipbbkgegfenjhklc"
)

Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "    Max's Downloader - 1-Click Host Setup" -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host ""

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ManifestPath = Join-Path $ScriptDir "com.maxsdownloader.host.json"
$BatPath = Join-Path $ScriptDir "run_host.bat"

# Update manifest JSON with fixed extension ID
$manifestContent = @{
    name = "com.maxsdownloader.host"
    description = "Max's Downloader Native Messaging Host"
    path = $BatPath
    type = "stdio"
    allowed_origins = @(
        "chrome-extension://$ExtensionId/"
    )
}

$manifestContent | ConvertTo-Json -Depth 5 | Set-Content -Path $ManifestPath -Encoding UTF8

# Create Windows Registry Key
$RegPath = "HKCU:\Software\Google\Chrome\NativeMessagingHosts\com.maxsdownloader.host"
try {
    if (-not (Test-Path $RegPath)) {
        New-Item -Path $RegPath -Force | Out-Null
    }
    Set-ItemProperty -Path $RegPath -Name "(default)" -Value $ManifestPath
    Write-Host "[v] Successfully registered host in Windows Registry:" -ForegroundColor Green
    Write-Host "    $RegPath -> $ManifestPath" -ForegroundColor Gray
} catch {
    Write-Host "[x] Registry write error: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "    Setup Complete! Extension is ready to use." -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan
