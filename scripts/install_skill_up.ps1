param([string]$Version = "latest", [string]$InstallDir = "$env:LOCALAPPDATA\skill-eval\bin")
$ErrorActionPreference = "Stop"
$repo = "alibaba/skill-up"
$os = "windows"; $arch = if ([Environment]::Is64BitOperatingSystem) { "amd64" } else { throw "Only Windows amd64 is supported by this installer" }
if ($Version -eq "latest") { $tag = (Invoke-RestMethod "https://api.github.com/repos/$repo/releases/latest").tag_name } else { $tag = if ($Version.StartsWith('v')) { $Version } else { "v$Version" } }
$ver = $tag.TrimStart('v'); $archive = "skill-up_${ver}_${os}_${arch}.zip"; $dir = Join-Path $env:TEMP ("skill-eval-" + [guid]::NewGuid()); New-Item -ItemType Directory $dir | Out-Null
try {
 Invoke-WebRequest "https://github.com/$repo/releases/download/$tag/$archive" -OutFile "$dir\$archive"
 $checks = Invoke-WebRequest "https://github.com/$repo/releases/download/$tag/skill-up_${ver}_checksums.txt"; $expected = ($checks.Content -split "`n" | Where-Object { $_ -match [regex]::Escape($archive) }) -split '\s+' | Select-Object -First 1
 $actual = (Get-FileHash "$dir\$archive" -Algorithm SHA256).Hash.ToLower(); if ($expected -and $actual -ne $expected.ToLower()) { throw "checksum mismatch" }
 Expand-Archive "$dir\$archive" -DestinationPath $dir -Force; New-Item -ItemType Directory -Force $InstallDir | Out-Null; Copy-Item "$dir\skill-up.exe" "$InstallDir\skill-up.exe" -Force
 Write-Host "Installed skill-up $ver to $InstallDir\skill-up.exe"
} finally { Remove-Item $dir -Recurse -Force -ErrorAction SilentlyContinue }
