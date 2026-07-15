# Teardown counterpart to install.ps1 (Story 4.6): removes everything the
# install + `uv run tools/setup-hooks.py` added. Destructive -- prints what it
# will remove and asks for confirmation unless the -Yes switch is passed (or,
# for the `irm | iex` piped form, set $env:AI_METRICS_UNINSTALL_YES = "1"
# before piping -- a switch parameter can't reach a script invoked that way).
#
# Usage:
#   .\uninstall.ps1 [-Yes]
#   $env:AI_METRICS_UNINSTALL_YES = "1"; irm <raw-url-to-this-file> | iex
#
# NOTE: never use `exit` here -- inside an iex-evaluated script, `exit`
# terminates the CALLER's whole PowerShell session, not just this script.
# Use `throw`/`return` for every non-error and error exit path instead.

param(
    [switch]$Yes
)

$ErrorActionPreference = "Stop"
$Marker = "installed by explore-jira-ai-metrics setup-hooks"
$SkipConfirm = $Yes -or ($env:AI_METRICS_UNINSTALL_YES -eq "1")

if (-not (Test-Path ".git")) {
    throw "not a git repository (no .git directory or file here) - cd to your repo root first"
}

$candidates = @(
    "tools", ".claude/skills/story-kickoff", "INSTALL.md", ".story-config.yaml.example",
    ".story-config.yaml", ".story.yaml", ".story-events.jsonl", ".story-events.pending.jsonl",
    ".active-story", ".active-claude-session", "snapshots", "metrics-reports"
)
$toRemove = @($candidates | Where-Object { Test-Path $_ })

$hookNames = @("post-commit", "post-checkout", "post-merge", "commit-msg")
foreach ($h in $hookNames) {
    $hookPath = ".git/hooks/$h"
    if ((Test-Path $hookPath) -and (Select-String -Path $hookPath -Pattern ([regex]::Escape($Marker)) -Quiet)) {
        $toRemove += $hookPath
    }
}

$settingsPath = ".claude/settings.json"
$hasSettings = Test-Path $settingsPath

if ($toRemove.Count -eq 0 -and -not $hasSettings) {
    Write-Host "Nothing to remove -- this repo has no capture tooling installed."
    return
}

Write-Host "The following will be removed:"
foreach ($p in $toRemove) { Write-Host "  $p" }
if ($hasSettings) {
    Write-Host "  (and this tooling's hook entries in $settingsPath -- other keys/entries are preserved)"
}

if (-not $SkipConfirm) {
    $ans = Read-Host "Proceed? [y/N]"
    if ($ans -notmatch '^(y|yes)$') {
        Write-Host "Aborted -- nothing removed."
        return
    }
}

foreach ($p in $toRemove) {
    Remove-Item -Recurse -Force $p
}

if ($hasSettings) {
    $settings = $null
    try {
        $settings = Get-Content $settingsPath -Raw | ConvertFrom-Json
    } catch {
        Write-Warning "could not parse $settingsPath ($($_.Exception.Message)) -- leaving it untouched"
    }
    if ($null -ne $settings -and ($settings.PSObject.Properties.Name -contains "hooks")) {
        $events = @("SessionStart", "SessionEnd", "PreToolUse", "PostToolUse", "Stop", "UserPromptSubmit")
        foreach ($event in $events) {
            if ($settings.hooks.PSObject.Properties.Name -contains $event) {
                $kept = @($settings.hooks.$event | Where-Object {
                    $entry = $_
                    $isOurs = $false
                    foreach ($h in $entry.hooks) {
                        if ($h.command -like "*tools/hooks/claude/*") { $isOurs = $true }
                    }
                    -not $isOurs
                })
                if ($kept.Count -gt 0) {
                    $settings.hooks.$event = $kept
                } else {
                    $settings.hooks.PSObject.Properties.Remove($event)
                }
            }
        }
        if (@($settings.hooks.PSObject.Properties).Count -eq 0) {
            $settings.PSObject.Properties.Remove("hooks")
        }
        # NOT `Set-Content -Encoding utf8` -- on Windows PowerShell 5.1 that writes a
        # real UTF-8 BOM, which setup-hooks.py's settings.json reader previously choked
        # on (a real user hit this exact crash after an uninstall->reinstall cycle).
        # [System.Text.UTF8Encoding($false)] writes BOM-less UTF-8 on both 5.1 and 7+.
        $json = $settings | ConvertTo-Json -Depth 10
        [System.IO.File]::WriteAllText(
            (Resolve-Path $settingsPath).Path, $json, (New-Object System.Text.UTF8Encoding($false))
        )
    }
}

Write-Host ""
Write-Host "Uninstalled."
