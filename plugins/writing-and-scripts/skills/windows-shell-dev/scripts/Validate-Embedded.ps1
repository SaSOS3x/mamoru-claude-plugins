<#
.SYNOPSIS
    Parse-validate every embedded PowerShell command inside a .cmd/.bat file,
    and optionally a PS1 test harness, using the real PowerShell parser.

.DESCRIPTION
    extract_ps.py gives a fast dependency-free lint, but only the actual
    PowerShell language parser can tell you a one-liner is genuinely valid.
    This script extracts each `powershell ... -Command "..."` body and runs it
    through [System.Management.Automation.Language.Parser]::ParseInput, and can
    also parse-check (and run) a harness such as tests/Run-Tests.ps1.

    Exit code is nonzero if any snippet or the harness fails to parse, so it
    slots into CI next to the batch analyzer.

.PARAMETER CmdFile
    Path to the .cmd/.bat file whose embedded PowerShell should be validated.

.PARAMETER Harness
    Optional path to a .ps1 test harness to parse-check.

.PARAMETER RunHarness
    If set, also execute the harness (after it parses cleanly).

.EXAMPLE
    pwsh -NoProfile -File Validate-Embedded.ps1 -CmdFile PerfTweaks.cmd
    pwsh -NoProfile -File Validate-Embedded.ps1 -CmdFile PerfTweaks.cmd -Harness tests/Run-Tests.ps1 -RunHarness
#>
param(
    [Parameter(Mandatory = $true)] [string] $CmdFile,
    [string] $Harness,
    [switch] $RunHarness
)

$ErrorActionPreference = 'Stop'
$failures = 0

function Test-Snippet([string] $code) {
    $errs = $null
    [System.Management.Automation.Language.Parser]::ParseInput(
        $code, [ref]$null, [ref]$errs) | Out-Null
    return $errs
}

if (-not (Test-Path $CmdFile)) {
    Write-Error "CmdFile not found: $CmdFile"
    exit 2
}

$text = [IO.File]::ReadAllText((Resolve-Path $CmdFile))

# Same shape as extract_ps.py: powershell|pwsh ... -Command "body", with \" treated
# as an escaped quote so commands containing literal quotes aren't truncated.
$rx = [regex]'(?i)\b(?:powershell|pwsh)\b[^"\r\n]*?\s(?:-Command|-c|/c)\s+"((?:[^"\\]|\\.)*)"'
$matches = $rx.Matches($text)

Write-Host "Found $($matches.Count) embedded PowerShell command(s) in $CmdFile"
$idx = 0
foreach ($m in $matches) {
    $idx++
    $code = $m.Groups[1].Value
    $errs = Test-Snippet $code
    if ($errs.Count -eq 0) {
        Write-Host ("  [OK ] snippet #{0} ({1} chars)" -f $idx, $code.Length)
    }
    else {
        $failures++
        $preview = $code.Substring(0, [Math]::Min(70, $code.Length))
        Write-Host ("  [BAD] snippet #{0}: {1}..." -f $idx, $preview)
        foreach ($e in $errs) { Write-Host ("        - " + $e.Message) }
    }
}

if ($Harness) {
    if (-not (Test-Path $Harness)) {
        Write-Error "Harness not found: $Harness"
        exit 2
    }
    $herrs = $null
    [System.Management.Automation.Language.Parser]::ParseFile(
        (Resolve-Path $Harness), [ref]$null, [ref]$herrs) | Out-Null
    if ($herrs.Count -eq 0) {
        Write-Host "Harness parses clean: $Harness"
    }
    else {
        $failures++
        Write-Host "Harness PARSE ERRORS in ${Harness}:"
        foreach ($e in $herrs) { Write-Host ("  - " + $e.Message) }
    }

    if ($RunHarness -and $herrs.Count -eq 0) {
        Write-Host "`n--- running harness ---"
        & (Resolve-Path $Harness)
        if ($LASTEXITCODE -ne 0) {
            $failures++
            Write-Host "Harness exited with code $LASTEXITCODE"
        }
    }
}

Write-Host ""
if ($failures -gt 0) {
    Write-Host "FAILED: $failures problem(s)."
    exit 1
}
Write-Host "All embedded PowerShell valid."
exit 0
