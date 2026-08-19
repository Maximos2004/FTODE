# Max's Downloader - PowerShell Native Messaging Host Installer
param (
    [string]$ExtensionId = "iabbelaamkcbkklcipbbkgegfenjhklc"
)

Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "    Max's Downloader - 1-Click Host Setup" -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host ""

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ChromeManifestPath = Join-Path $ScriptDir "com.maxsdownloader.host.json"
$FirefoxManifestPath = Join-Path $ScriptDir "com.maxsdownloader.host-firefox.json"
$BatPath = Join-Path $ScriptDir "run_host.bat"

# 1. Update Chrome/Chromium manifest JSON
$chromeManifestContent = @{
    name = "com.maxsdownloader.host"
    description = "Max's Downloader Native Messaging Host"
    path = $BatPath
    type = "stdio"
    allowed_origins = @(
        "chrome-extension://$ExtensionId/"
    )
}
$chromeManifestContent | ConvertTo-Json -Depth 5 | Set-Content -Path $ChromeManifestPath -Encoding UTF8

# 2. Update Firefox manifest JSON
$firefoxManifestContent = @{
    name = "com.maxsdownloader.host"
    description = "Max's Downloader Native Messaging Host"
    path = $BatPath
    type = "stdio"
    allowed_extensions = @(
        "maxs-downloader@maxakt.local"
    )
}
$firefoxManifestContent | ConvertTo-Json -Depth 5 | Set-Content -Path $FirefoxManifestPath -Encoding UTF8

# Create Windows Registry Keys for Chrome, Edge, Chromium, and Firefox
$RegMappings = @(
    @{ Path = "HKCU:\Software\Google\Chrome\NativeMessagingHosts\com.maxsdownloader.host"; Manifest = $ChromeManifestPath; Browser = "Google Chrome" },
    @{ Path = "HKCU:\Software\Microsoft\Edge\NativeMessagingHosts\com.maxsdownloader.host"; Manifest = $ChromeManifestPath; Browser = "Microsoft Edge" },
    @{ Path = "HKCU:\Software\Chromium\NativeMessagingHosts\com.maxsdownloader.host"; Manifest = $ChromeManifestPath; Browser = "Chromium / Opera / Brave" },
    @{ Path = "HKCU:\Software\Mozilla\NativeMessagingHosts\com.maxsdownloader.host"; Manifest = $FirefoxManifestPath; Browser = "Mozilla Firefox" }
)

foreach ($entry in $RegMappings) {
    try {
        if (-not (Test-Path $entry.Path)) {
            New-Item -Path $entry.Path -Force | Out-Null
        }
        Set-ItemProperty -Path $entry.Path -Name "(default)" -Value $entry.Manifest
        Write-Host "[v] Successfully registered for $($entry.Browser):" -ForegroundColor Green
        Write-Host "    $($entry.Path) -> $($entry.Manifest)" -ForegroundColor Gray
    } catch {
        Write-Host "[x] Registry write error for $($entry.Browser): $_" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "    Setup Complete! Extension is ready to use." -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan
