# PowerShell build script for Pharmly / PharmaBharat APK
# Uses official Gradle release build and signs with release.jks

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $scriptDir

# Check Android SDK
if ($env:ANDROID_HOME -and (Test-Path $env:ANDROID_HOME)) {
    $SDK = $env:ANDROID_HOME
} elseif (Test-Path "H:\AndroidSDK") {
    $SDK = "H:\AndroidSDK"
    $env:ANDROID_HOME = $SDK
} elseif (Test-Path "$env:LOCALAPPDATA\Android\Sdk") {
    $SDK = "$env:LOCALAPPDATA\Android\Sdk"
    $env:ANDROID_HOME = $SDK
} else {
    Write-Error "Android SDK not found. Set `$env:ANDROID_HOME."
    exit 1
}

Write-Host "Using Android SDK: $SDK" -ForegroundColor Cyan

# Locate Gradle binary
$gradleBat = Join-Path $scriptDir "gradle-8.4\bin\gradle.bat"
if (!(Test-Path $gradleBat)) {
    if (Test-Path (Join-Path $scriptDir "gradlew.bat")) {
        $gradleBat = Join-Path $scriptDir "gradlew.bat"
    } else {
        Write-Error "Gradle binary not found at $gradleBat"
        exit 1
    }
}

Write-Host "Building Release APK with Gradle..." -ForegroundColor Yellow
& $gradleBat assembleRelease --no-daemon

$builtApk = Join-Path $scriptDir "app\build\outputs\apk\release\app-release.apk"
if (!(Test-Path $builtApk)) {
    Write-Error "Build failed: $builtApk not found"
    exit 1
}

$mainApk = Join-Path $scriptDir "..\Pharmly.apk"
Copy-Item $builtApk -Destination $mainApk -Force
Write-Host "Copied to $mainApk" -ForegroundColor Green

Write-Host "APK Build Successful! Single official APK: Pharmly.apk" -ForegroundColor Green
