# PowerShell build script for Pharmly / PharmaBharat APK
# Uses official Gradle release build and signs with release.jks

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $scriptDir

# Check Java 17
if (Test-Path "C:\Program Files\Eclipse Adoptium\jdk-17.0.16.8-hotspot") {
    $env:JAVA_HOME = "C:\Program Files\Eclipse Adoptium\jdk-17.0.16.8-hotspot"
} elseif (Test-Path "C:\Program Files\Java\jdk-17") {
    $env:JAVA_HOME = "C:\Program Files\Java\jdk-17"
}
Write-Host "Using JAVA_HOME: $env:JAVA_HOME" -ForegroundColor Cyan

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

# Remove any old build output
$builtApk = Join-Path $scriptDir "app\build\outputs\apk\release\app-release.apk"
if (Test-Path $builtApk) {
    Remove-Item $builtApk -Force
}

Write-Host "Building Release APK with Gradle..." -ForegroundColor Yellow
& $gradleBat assembleRelease --no-daemon

if ($LASTEXITCODE -ne 0) {
    Write-Error "Gradle build failed with exit code $LASTEXITCODE"
    exit 1
}

if (!(Test-Path $builtApk)) {
    Write-Error "Build failed: $builtApk not found"
    exit 1
}

$mainApk = Join-Path $scriptDir "..\Pharmly.apk"
Copy-Item $builtApk -Destination $mainApk -Force
Write-Host "Copied to $mainApk" -ForegroundColor Green

# Also copy to root workspace so all root APKs are always up to date
$rootApk = "H:\Pharmly\Pharmly.apk"
$rootProApk = "H:\Pharmly\PharmlyPro.apk"
$rootPharmaBharatProApk = "H:\Pharmly\PharmaBharatPro.apk"
Copy-Item $builtApk -Destination $rootApk -Force
Copy-Item $builtApk -Destination $rootProApk -Force
Copy-Item $builtApk -Destination $rootPharmaBharatProApk -Force
Write-Host "Copied to $rootApk, $rootProApk, and $rootPharmaBharatProApk" -ForegroundColor Green

Write-Host "APK Build Successful! Official APK: Pharmly.apk (Version 3.7.5, Code 16)" -ForegroundColor Green
