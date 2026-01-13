Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Policy:
# - If P0 (preconditions) fails -> mark subsequent tests as SKIP(precondition_failed)
# - "Quarantine" tests (like P2.1 multi-worker) are SKIP unless explicit flag enabled
# - Collect-all: run everything that is eligible; do NOT fail-fast
# - Exit code:
#   - 0 if no FAIL
#   - 1 if any FAIL
#   - 2 if P0 failed (optional; you can still use 1 if you prefer)
#
# Recommended test ordering:
#   P0 -> P1 -> P3 -> P2 (lock) -> quarantine tests

function Get-RunnerConfig {
    param(
        [switch]$EnableMultiWorker = $false
    )

    return [pscustomobject]@{
        enable_multi_worker = [bool]$EnableMultiWorker
        tests_root = "runtime/tests"
        meta_path  = "runtime/tests/_meta.json"
        final_report_path = "runtime/tests/FINAL_REPORT.json"
    }
}

function Write-RunMeta {
    param(
        [Parameter(Mandatory=$true)][pscustomobject]$Config,
        [hashtable]$Extra = @{}
    )

    New-Item -ItemType Directory -Path $Config.tests_root -Force | Out-Null

    $meta = @{
        timestamp = (Get-Date).ToString("o")
        machine = @{
            computer_name = $env:COMPUTERNAME
            user = $env:USERNAME
            os = (Get-CimInstance Win32_OperatingSystem | Select-Object -ExpandProperty Caption)
        }
        config = @{
            enable_multi_worker = $Config.enable_multi_worker
        }
    } + $Extra

    $meta | ConvertTo-Json -Depth 8 | Out-File -FilePath $Config.meta_path -Encoding utf8
    return $Config.meta_path
}

function Should-SkipQuarantineTest {
    param(
        [Parameter(Mandatory=$true)][string]$TestName,
        [Parameter(Mandatory=$true)][pscustomobject]$Config
    )

    if ($TestName -eq "test_p2_multi_worker") {
        return (-not $Config.enable_multi_worker)
    }

    return $false
}

function Mark-Skipped {
    param(
        [Parameter(Mandatory=$true)][string]$TestName,
        [Parameter(Mandatory=$true)][string]$Reason,
        [Parameter(Mandatory=$true)][string]$TestsRoot
    )

    . "$PSScriptRoot\_helpers.ps1"

    $testDir = New-TestDir -Root $TestsRoot -TestName $TestName
    $res = New-TestResult -Test $TestName -Pass $true -Status "SKIP" -SkipReason $Reason -DurationMs 0 -Metrics @{} -Artifacts @()
    Write-TestReport -Result $res -TestDir $testDir
    return $res
}

function Finalize-Report {
    param(
        [Parameter(Mandatory=$true)][pscustomobject]$Config,
        [Parameter(Mandatory=$true)][System.Collections.Generic.List[object]]$Results
    )

    $passed = @($Results | Where-Object { $null -ne $_.status -and $_.status -eq "PASS" }).Count
    $failed = @($Results | Where-Object { $null -ne $_.status -and $_.status -eq "FAIL" }).Count
    $skipped = @($Results | Where-Object { $null -ne $_.status -and $_.status -eq "SKIP" }).Count

    $final = @{
        timestamp = (Get-Date).ToString("o")
        total_tests = $Results.Count
        passed = $passed
        failed = $failed
        skipped = $skipped
        meta = @{
            meta_path = $Config.meta_path
        }
        tests = $Results
    }

    New-Item -ItemType Directory -Path $Config.tests_root -Force | Out-Null
    $final | ConvertTo-Json -Depth 14 | Out-File -FilePath $Config.final_report_path -Encoding utf8

    return $final
}

function Get-ExitCode {
    param(
        [Parameter(Mandatory=$true)][hashtable]$FinalReport,
        [bool]$TreatP0FailureAs2 = $true
    )

    if ($FinalReport.failed -gt 0) { return 1 }

    # Optional: if you encode a specific P0 test name, you can elevate exit code.
    if ($TreatP0FailureAs2) {
        $p0 = @($FinalReport.tests | Where-Object { $_.test -like "test_p0_*" -and $_.status -eq "FAIL" })
        if ($p0.Count -gt 0) { return 2 }
    }

    return 0
}
