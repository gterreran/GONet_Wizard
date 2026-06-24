<#
Build the local Windows installer for GONet Wizard.

This script wraps two steps:
  1. Optionally build the PyInstaller one-dir GUI app.
  2. Run Inno Setup to create a user-local Setup.exe installer.

Run from the repository root, or from any location inside the repository:

  powershell -ExecutionPolicy Bypass -File build_tools\windows\build_installer.ps1 -ForcePyInstaller
#>

[CmdletBinding()]
param(
    [switch]$ForcePyInstaller,
    [switch]$SkipPyInstaller,
    [string]$Version = "",
    [string]$InnoSetupCompiler = "",
    [string]$SourceDir = "",
    [string]$OutputDir = "",
    [switch]$NoChecksum
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

function Resolve-RepositoryRoot {
    $scriptDir = Split-Path -Parent $PSCommandPath
    return (Resolve-Path (Join-Path $scriptDir "..\..")).Path
}

function Resolve-PythonVersion {
    param([string]$RepositoryRoot)

    if ($Version.Trim()) {
        return $Version.Trim()
    }

    $gitVersion = (& git -C $RepositoryRoot describe --tags --always --dirty 2>$null)
    if ($LASTEXITCODE -eq 0 -and $gitVersion) {
        $gitVersion = ($gitVersion | Select-Object -First 1).ToString().Trim()
        if ($gitVersion) {
            return ($gitVersion -replace '^v', '')
        }
    }

    try {
        $detected = (& python -c "import importlib.metadata as m; print(m.version('GONet_Wizard'))" 2>$null)
        if ($LASTEXITCODE -eq 0 -and $detected) {
            $detected = ($detected | Select-Object -First 1).ToString().Trim()
            if ($detected) {
                return $detected
            }
        }
    }
    catch {
        # Fall through to the local fallback below.
    }

    return "0.0.0-windows-local"
}

function Convert-ToSafeFileVersion {
    param([string]$RawVersion)
    return ($RawVersion -replace '[^0-9A-Za-z._-]', '-')
}

function Convert-ToWindowsFileVersion {
    param([string]$RawVersion)

    $matches = [regex]::Matches($RawVersion, '\d+')
    $parts = @()

    foreach ($match in $matches) {
        if ($parts.Count -ge 4) {
            break
        }
        $parts += $match.Value
    }

    while ($parts.Count -lt 4) {
        $parts += "0"
    }

    return ($parts -join ".")
}

function Resolve-InnoSetupCompiler {
    param([string]$RequestedCompiler)

    if ($RequestedCompiler.Trim()) {
        if (-not (Test-Path $RequestedCompiler)) {
            throw "The requested Inno Setup compiler was not found: $RequestedCompiler"
        }
        return (Resolve-Path $RequestedCompiler).Path
    }

    $command = Get-Command "ISCC.exe" -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    $programFilesX86 = [Environment]::GetEnvironmentVariable("ProgramFiles(x86)")
    $programFiles = [Environment]::GetEnvironmentVariable("ProgramFiles")

    $candidates = @()
    if ($programFilesX86) {
        $candidates += Join-Path $programFilesX86 "Inno Setup 6\ISCC.exe"
    }
    if ($programFiles) {
        $candidates += Join-Path $programFiles "Inno Setup 6\ISCC.exe"
    }

    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path $candidate)) {
            return (Resolve-Path $candidate).Path
        }
    }

    throw @"
Could not find ISCC.exe, the Inno Setup compiler.

Install Inno Setup 6, add ISCC.exe to PATH, or pass:
  -InnoSetupCompiler "C:\Path\To\ISCC.exe"
"@
}

if ($ForcePyInstaller -and $SkipPyInstaller) {
    throw "Use either -ForcePyInstaller or -SkipPyInstaller, not both."
}

$repoRoot = Resolve-RepositoryRoot
$issPath = Join-Path $repoRoot "build_tools\windows\gonet_wizard.iss"
$specPath = Join-Path $repoRoot "build_tools\pyinstaller\gonet_wizard_gui.spec"

if (-not (Test-Path $issPath)) {
    throw "Inno Setup script not found: $issPath"
}

if (-not (Test-Path $specPath)) {
    throw "PyInstaller spec not found: $specPath"
}

$resolvedSourceDir = if ($SourceDir.Trim()) {
    (Resolve-Path $SourceDir).Path
} else {
    Join-Path $repoRoot "dist\GONet Wizard"
}

$resolvedOutputDir = if ($OutputDir.Trim()) {
    if (-not (Test-Path $OutputDir)) {
        New-Item -ItemType Directory -Path $OutputDir | Out-Null
    }
    (Resolve-Path $OutputDir).Path
} else {
    Join-Path $repoRoot "dist"
}

if (-not (Test-Path $resolvedOutputDir)) {
    New-Item -ItemType Directory -Path $resolvedOutputDir | Out-Null
}

$shouldRunPyInstaller = -not $SkipPyInstaller -and ($ForcePyInstaller -or -not (Test-Path $resolvedSourceDir))

if ($shouldRunPyInstaller) {
    Write-Step "Building frozen GUI app with PyInstaller"
    Push-Location $repoRoot
    try {
        & python -m PyInstaller $specPath --clean --noconfirm
        if ($LASTEXITCODE -ne 0) {
            throw "PyInstaller failed with exit code $LASTEXITCODE."
        }
    }
    finally {
        Pop-Location
    }
} else {
    Write-Step "Reusing existing PyInstaller output"
}

$exePath = Join-Path $resolvedSourceDir "GONet Wizard.exe"
if (-not (Test-Path $exePath)) {
    throw "Frozen GUI executable not found: $exePath"
}

$appVersion = Resolve-PythonVersion -RepositoryRoot $repoRoot
$safeVersion = Convert-ToSafeFileVersion -RawVersion $appVersion
$appFileVersion = Convert-ToWindowsFileVersion -RawVersion $appVersion
$outputBaseFilename = "GONet-Wizard-$safeVersion-Windows-x64-unsigned-Setup"
$iscc = Resolve-InnoSetupCompiler -RequestedCompiler $InnoSetupCompiler

Write-Step "Building Windows installer with Inno Setup"
Write-Host "Repository root : $repoRoot"
Write-Host "Source folder   : $resolvedSourceDir"
Write-Host "Output folder   : $resolvedOutputDir"
Write-Host "Version         : $appVersion"
Write-Host "File version    : $appFileVersion"
Write-Host "Compiler        : $iscc"

$isccArgs = @(
    "/DAppVersion=$appVersion",
    "/DAppFileVersion=$appFileVersion",
    "/DSourceDir=$resolvedSourceDir",
    "/DOutputDir=$resolvedOutputDir",
    "/DOutputBaseFilename=$outputBaseFilename",
    $issPath
)

Push-Location $repoRoot
try {
    & $iscc @isccArgs

    if ($LASTEXITCODE -ne 0) {
        throw "Inno Setup failed with exit code $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}

$installerPath = Join-Path $resolvedOutputDir "$outputBaseFilename.exe"
if (-not (Test-Path $installerPath)) {
    throw "Installer was not created: $installerPath"
}

Write-Step "Installer created"
Write-Host $installerPath -ForegroundColor Green

if (-not $NoChecksum) {
    $checksumPath = Join-Path $resolvedOutputDir "SHA256SUMS-Windows.txt"
    $hash = Get-FileHash -Algorithm SHA256 $installerPath
    "{0}  {1}" -f $hash.Hash.ToLowerInvariant(), (Split-Path -Leaf $installerPath) | Set-Content -Encoding ASCII $checksumPath
    Write-Host "Checksum file  : $checksumPath" -ForegroundColor Green
}
