# PowerShell build script for PharmaBharatPro.apk
# No Android Studio needed! Builds in 5 seconds.

$ErrorActionPreference = "Stop"
$SDK = "$env:LOCALAPPDATA\Android\Sdk"

if (!(Test-Path $SDK)) {
    Write-Error "Android SDK not found at $SDK"
    exit 1
}

# Find build-tools
$BUILD_TOOLS_DIR = Get-ChildItem "$SDK\build-tools" | Sort-Object Name -Descending | Select-Object -First 1 -ExpandProperty FullName
$PLATFORM = Get-ChildItem "$SDK\platforms" | Sort-Object Name -Descending | Select-Object -First 1 -ExpandProperty FullName

$AAPT2 = "$BUILD_TOOLS_DIR\aapt2.exe"
$D8 = "$BUILD_TOOLS_DIR\d8.bat"
$ZIPALIGN = "$BUILD_TOOLS_DIR\zipalign.exe"
$APKSIGNER = "$BUILD_TOOLS_DIR\apksigner.bat"
$ANDROID_JAR = "$PLATFORM\android.jar"

Write-Host "Using Build Tools: $BUILD_TOOLS_DIR" -ForegroundColor Cyan
Write-Host "Using Target Platform: $PLATFORM" -ForegroundColor Cyan

# 1. Clean build_tmp
Remove-Item -Recurse -Force "build_tmp" -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path "build_tmp", "build_tmp/gen", "build_tmp/bin", "build_tmp/dex" -Force | Out-Null

# 2. Compile & Link Resources
Write-Host "[1/5] Compiling resources..." -ForegroundColor Yellow
& $AAPT2 compile --dir app/src/main/res -o build_tmp/compiled.zip
& $AAPT2 link -I $ANDROID_JAR --manifest app/src/main/AndroidManifest.xml -o build_tmp/unaligned.apk --java build_tmp/gen build_tmp/compiled.zip

# 3. Compile Java Sources
Write-Host "[2/5] Compiling Java code..." -ForegroundColor Yellow
javac -cp $ANDROID_JAR -d build_tmp/bin build_tmp/gen/com/pharmabharat/app/R.java app/src/main/java/com/pharmabharat/app/MainActivity.java

# 4. DEX compilation
Write-Host "[3/5] Converting to DEX bytecode..." -ForegroundColor Yellow
$CLASS_FILES = Get-ChildItem -Path build_tmp/bin/com/pharmabharat/app/*.class | Select-Object -ExpandProperty FullName
& $D8 --lib $ANDROID_JAR --output build_tmp/dex $CLASS_FILES

# 5. Package DEX into APK
Write-Host "[4/5] Packaging APK..." -ForegroundColor Yellow
python -c "import zipfile; z = zipfile.ZipFile('build_tmp/unaligned.apk', 'a'); z.write('build_tmp/dex/classes.dex', 'classes.dex'); z.close()"

# 6. Zip-align
Write-Host "[5/5] Aligning and signing APK..." -ForegroundColor Yellow
& $ZIPALIGN -f -v 4 build_tmp/unaligned.apk build_tmp/aligned.apk | Out-Null

# 7. Generate Keystore if missing & Sign
if (!(Test-Path "build_tmp/debug.keystore")) {
    keytool -genkey -v -keystore build_tmp/debug.keystore -storepass android -alias androiddebugkey -keypass android -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=PharmaBharat,OU=Mobile,O=PharmaBharat,C=IN" | Out-Null
}

& $APKSIGNER sign --ks build_tmp/debug.keystore --ks-pass pass:android --key-pass pass:android --out PharmaBharatPro.apk build_tmp/aligned.apk
Copy-Item "PharmaBharatPro.apk" -Destination "../PharmaBharatPro.apk" -Force

Write-Host "SUCCESS! Signed APK built at: $(Resolve-Path ../PharmaBharatPro.apk)" -ForegroundColor Green
