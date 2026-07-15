# One-command installer (Story 4.3): fetches the latest release zip of
# ai-project-metrics-bmad and extracts it at the current directory's root.
# Usage: irm <raw-url-to-this-file> | iex
#
# NOTE: this script is designed to run via `irm | iex` in the caller's own
# terminal session. Never call `exit` here — inside an iex-evaluated script,
# `exit` terminates the CALLER's whole PowerShell session, not just this
# script. Use `throw` for every failure path instead.

$ErrorActionPreference = "Stop"
$Repo = "jayanthchincholi26/ai-project-metrics-bmad"

if (-not (Test-Path ".git")) {
    throw "not a git repository (no .git directory here) - cd to your repo root first"
}

Write-Host "Fetching latest release info for $Repo..."
$release = Invoke-RestMethod -Uri "https://api.github.com/repos/$Repo/releases/latest"
$asset = $release.assets | Where-Object { $_.name -like "*.zip" } | Select-Object -First 1

if (-not $asset) {
    throw "could not find a .zip asset on the latest release of $Repo"
}

$tmpZip = Join-Path ([System.IO.Path]::GetTempPath()) "$([System.IO.Path]::GetRandomFileName()).zip"
Write-Host "Downloading $($asset.browser_download_url)..."
Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $tmpZip

Write-Host "Extracting into $(Get-Location)..."
Expand-Archive -Path $tmpZip -DestinationPath . -Force
Remove-Item $tmpZip

Write-Host ""
Write-Host "Installed. Next: uv run tools/setup-hooks.py --repo-root ."
