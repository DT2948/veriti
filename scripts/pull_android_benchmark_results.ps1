[CmdletBinding()]
param(
    [switch]$RunBenchmark,
    [ValidateRange(0, 1000)]
    [int]$Warmups = 5,
    [ValidateRange(1, 10000)]
    [Nullable[int]]$Repetitions,
    [string]$FixtureDirectory = "privacy",
    [string]$OutputRoot = "benchmark_results/android"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$AndroidRoot = Join-Path $RepoRoot "mobile/android"
$GradleFile = Join-Path $AndroidRoot "app/build.gradle.kts"
$script:AdbPath = $null
$script:Serial = $null

function Stop-WithError {
    param([string]$Message)
    Write-Error $Message
    exit 1
}

function Find-Adb {
    $command = Get-Command adb -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    $fallback = Join-Path $env:LOCALAPPDATA "Android/Sdk/platform-tools/adb.exe"
    if (Test-Path -LiteralPath $fallback) {
        return $fallback
    }

    Stop-WithError "adb was not found on PATH or at $fallback. Install Android SDK Platform Tools."
}

function Invoke-AdbText {
    param(
        [Parameter(Mandatory)]
        [string[]]$Arguments,
        [switch]$AllowFailure
    )

    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $output = & $script:AdbPath -s $script:Serial @Arguments 2>&1
        $exitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previousPreference
    }
    $text = (($output | ForEach-Object { "$_" }) -join [Environment]::NewLine).Trim()
    if ($exitCode -ne 0 -and -not $AllowFailure) {
        throw "adb command failed with exit code $exitCode. $text"
    }
    return $text
}

function Initialize-Device {
    $script:AdbPath = Find-Adb
    $output = & $script:AdbPath devices 2>&1
    if ($LASTEXITCODE -ne 0) {
        Stop-WithError "adb devices failed: $($output -join ' ')"
    }

    $devices = @()
    foreach ($line in $output) {
        if ("$line" -match '^(\S+)\s+(device|unauthorized|offline|unknown)$') {
            $devices += [pscustomobject]@{ Serial = $Matches[1]; State = $Matches[2] }
        }
    }
    if ($devices.Count -ne 1) {
        $states = if ($devices.Count) {
            ($devices | ForEach-Object { "$($_.Serial)=$($_.State)" }) -join ", "
        } else {
            "none"
        }
        Stop-WithError "Expected exactly one connected Android device; found $($devices.Count): $states"
    }
    if ($devices[0].State -ne "device") {
        Stop-WithError "Device $($devices[0].Serial) is $($devices[0].State), not authorized and ready."
    }

    $script:Serial = $devices[0].Serial
    Write-Host "Using adb: $script:AdbPath"
    Write-Host "Connected device: $script:Serial"
}

function Add-Candidate {
    param(
        [System.Collections.Generic.List[string]]$Candidates,
        [System.Collections.Generic.HashSet[string]]$Seen,
        [string]$Value
    )
    $candidate = $Value.Trim()
    if ($candidate -match '^[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z0-9_]+)+$' -and $Seen.Add($candidate)) {
        $Candidates.Add($candidate)
    }
}

function Get-SdkRoot {
    foreach ($value in @($env:ANDROID_SDK_ROOT, $env:ANDROID_HOME)) {
        if ($value -and (Test-Path -LiteralPath $value)) {
            return $value
        }
    }
    $fallback = Join-Path $env:LOCALAPPDATA "Android/Sdk"
    if (Test-Path -LiteralPath $fallback) {
        return $fallback
    }
    return $null
}

function Get-ApplicationCandidates {
    $candidates = New-Object 'System.Collections.Generic.List[string]'
    $seen = New-Object 'System.Collections.Generic.HashSet[string]'

    if (Test-Path -LiteralPath $GradleFile) {
        $gradle = Get-Content -LiteralPath $GradleFile -Raw
        $idMatch = [regex]::Match($gradle, 'applicationId\s*=\s*"([^"]+)"')
        if ($idMatch.Success) {
            $applicationId = $idMatch.Groups[1].Value
            $debugMatch = [regex]::Match(
                $gradle,
                '(?ms)^\s*debug\s*\{(?<body>.*?)(?=^\s*\})'
            )
            if ($debugMatch.Success) {
                $suffixMatch = [regex]::Match(
                    $debugMatch.Groups["body"].Value,
                    'applicationIdSuffix\s*=\s*"([^"]+)"'
                )
                if ($suffixMatch.Success) {
                    $applicationId += $suffixMatch.Groups[1].Value
                }
            }
            Add-Candidate $candidates $seen $applicationId
        }
    }

    $apk = Join-Path $AndroidRoot "app/build/outputs/apk/debug/app-debug.apk"
    $sdkRoot = Get-SdkRoot
    if ((Test-Path -LiteralPath $apk) -and $sdkRoot) {
        $buildTools = Get-ChildItem -LiteralPath (Join-Path $sdkRoot "build-tools") -Directory -ErrorAction SilentlyContinue |
            Sort-Object Name -Descending
        foreach ($directory in $buildTools) {
            foreach ($toolName in @("aapt.exe", "aapt2.exe")) {
                $tool = Join-Path $directory.FullName $toolName
                if (Test-Path -LiteralPath $tool) {
                    $badging = & $tool dump badging $apk 2>&1
                    if ("$badging" -match "package:\s+name='([^']+)'") {
                        Add-Candidate $candidates $seen $Matches[1]
                    }
                    break
                }
            }
        }

        $apkAnalyzer = Join-Path $sdkRoot "cmdline-tools/latest/bin/apkanalyzer.bat"
        if (Test-Path -LiteralPath $apkAnalyzer) {
            $analyzedId = & $apkAnalyzer manifest application-id $apk 2>$null
            if ($LASTEXITCODE -eq 0 -and $analyzedId) {
                Add-Candidate $candidates $seen "$analyzedId"
            }
        }
    }

    $intermediates = Join-Path $AndroidRoot "app/build/intermediates"
    if (Test-Path -LiteralPath $intermediates) {
        Get-ChildItem -LiteralPath $intermediates -Filter AndroidManifest.xml -Recurse -File -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -match '[\\/]debug[\\/]' } |
            Select-Object -First 20 |
            ForEach-Object {
                $manifestText = Get-Content -LiteralPath $_.FullName -Raw
                if ($manifestText -match '<manifest[^>]+\bpackage="([^"]+)"') {
                    Add-Candidate $candidates $seen $Matches[1]
                }
            }
    }

    $installed = Invoke-AdbText -Arguments @(
        "shell", "pm", "list", "packages", "--user", "0"
    ) -AllowFailure
    foreach ($line in ($installed -split '\r?\n')) {
        if ($line -match '^package:(.+)$' -and $Matches[1] -match '(?i)veriti') {
            Add-Candidate $candidates $seen $Matches[1]
        }
    }

    return @($candidates)
}

function Test-RemoteFile {
    param([string]$Path)
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & $script:AdbPath -s $script:Serial shell test -f $Path 2>$null
        return $LASTEXITCODE -eq 0
    } finally {
        $ErrorActionPreference = $previousPreference
    }
}

function Test-RunAsFile {
    param([string]$Package, [string]$Path)
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & $script:AdbPath -s $script:Serial shell run-as --user 0 $Package test -f $Path 2>$null
        return $LASTEXITCODE -eq 0
    } finally {
        $ErrorActionPreference = $previousPreference
    }
}

function Find-ApplicationId {
    $candidates = @(Get-ApplicationCandidates)
    if (-not $candidates.Count) {
        Stop-WithError "No application ID candidates were found from Gradle, APK metadata, manifests, or installed user-0 packages."
    }

    $evaluated = @()
    foreach ($candidate in $candidates) {
        $pmPath = Invoke-AdbText -Arguments @(
            "shell", "pm", "path", "--user", "0", $candidate
        ) -AllowFailure
        $installed = $pmPath -match '^package:'
        $storagePath = "/storage/emulated/0/Android/data/$candidate/files/benchmark_results"
        $sdcardPath = "/sdcard/Android/data/$candidate/files/benchmark_results"
        $direct = (Test-RemoteFile "$storagePath/android-privacy-summary.json") -or
            (Test-RemoteFile "$sdcardPath/android-privacy-summary.json")
        $runAs = Test-RunAsFile $candidate "$storagePath/android-privacy-summary.json"
        $score = 0
        if ($installed) { $score += 1 }
        if ($direct) { $score += 4 }
        if ($runAs) { $score += 2 }
        $evaluated += [pscustomobject]@{
            Package = $candidate
            Installed = $installed
            DirectFiles = $direct
            RunAsFiles = $runAs
            Score = $score
        }
    }

    $evaluated | Format-Table Package, Installed, DirectFiles, RunAsFiles, Score -AutoSize | Out-Host
    $ranked = @($evaluated | Where-Object Installed | Sort-Object Score -Descending)
    if (-not $ranked.Count) {
        Stop-WithError "None of the detected application IDs is installed for Android user 0."
    }
    $best = @($ranked | Where-Object Score -eq $ranked[0].Score)
    if ($best.Count -gt 1 -and $best[0].Score -gt 1) {
        Stop-WithError "Multiple installed packages contain plausible benchmark files: $($best.Package -join ', ')"
    }

    Write-Host "Detected application ID: $($ranked[0].Package)"
    return $ranked[0].Package
}

function Invoke-Benchmark {
    $assetDirectory = Join-Path $AndroidRoot "app/src/androidTest/assets/$FixtureDirectory"
    $manifest = Join-Path $assetDirectory "manifest.json"
    if (-not (Test-Path -LiteralPath $manifest)) {
        $generator = Join-Path $RepoRoot "scripts/generate_privacy_benchmark_fixtures.py"
        Write-Host "Generating Android benchmark fixtures in $assetDirectory"
        & python $generator --profile full --output $assetDirectory
        if ($LASTEXITCODE -ne 0) {
            Stop-WithError "Android benchmark fixture generation failed."
        }
    }

    $gradlew = Join-Path $AndroidRoot "gradlew.bat"
    if (-not (Test-Path -LiteralPath $gradlew)) {
        Stop-WithError "Gradle wrapper not found at $gradlew"
    }

    Write-Host "Building Android privacy benchmark APKs..."
    Push-Location $AndroidRoot
    try {
        & $gradlew assembleDebug assembleDebugAndroidTest
        if ($LASTEXITCODE -ne 0) {
            Stop-WithError "Android benchmark APK build failed with exit code $LASTEXITCODE."
        }
    } finally {
        Pop-Location
    }

    $appApk = Join-Path $AndroidRoot "app/build/outputs/apk/debug/app-debug.apk"
    $testApk = Join-Path $AndroidRoot "app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk"
    foreach ($apk in @($appApk, $testApk)) {
        if (-not (Test-Path -LiteralPath $apk)) {
            Stop-WithError "Expected benchmark APK was not produced: $apk"
        }
        & $script:AdbPath -s $script:Serial install --user 0 -r $apk 2>&1 | Out-Host
        if ($LASTEXITCODE -ne 0) {
            Stop-WithError "Failed to install benchmark APK for Android user 0: $apk"
        }
    }

    $manifestCandidates = @(Get-ChildItem -LiteralPath (Join-Path $AndroidRoot "app/build/intermediates") `
        -Filter AndroidManifest.xml -Recurse -File -ErrorAction SilentlyContinue | `
        Where-Object { $_.FullName -match 'debugAndroidTest' })
    $runner = $null
    foreach ($manifestFile in $manifestCandidates) {
        $manifestText = Get-Content -LiteralPath $manifestFile.FullName -Raw
        $packageMatch = [regex]::Match($manifestText, '<manifest[^>]+\bpackage="([^"]+)"')
        $instrumentMatch = [regex]::Match($manifestText, '(?s)<instrumentation\b.*?/>')
        if (-not $packageMatch.Success -or -not $instrumentMatch.Success) { continue }
        $nameMatch = [regex]::Match($instrumentMatch.Value, 'android:name="([^"]+)"')
        $targetMatch = [regex]::Match($instrumentMatch.Value, 'android:targetPackage="([^"]+)"')
        if (-not $nameMatch.Success -or -not $targetMatch.Success) { continue }

        $testPackage = $packageMatch.Groups[1].Value
        $targetPackage = $targetMatch.Groups[1].Value
        $testInstalled = Invoke-AdbText -Arguments @(
            "shell", "pm", "path", "--user", "0", $testPackage
        ) -AllowFailure
        $targetInstalled = Invoke-AdbText -Arguments @(
            "shell", "pm", "path", "--user", "0", $targetPackage
        ) -AllowFailure
        if ($testInstalled -match '^package:' -and $targetInstalled -match '^package:') {
            $runner = "$testPackage/$($nameMatch.Groups[1].Value)"
            break
        }
    }
    if (-not $runner) {
        Stop-WithError "Could not discover a generated instrumentation manifest whose test and target packages are installed for Android user 0."
    }

    $instrumentArguments = @(
        "shell", "am", "instrument", "--user", "0", "-w", "-r",
        "-e", "class", "com.veriti.app.pipeline.PrivacyBenchmarkTest#benchmarkPrivacyPipeline",
        "-e", "warmups", "$Warmups",
        "-e", "fixtureDirectory", $FixtureDirectory
    )
    if ($null -ne $Repetitions) {
        $instrumentArguments += @("-e", "repetitions", "$Repetitions")
    }
    $instrumentArguments += $runner

    Write-Host "Running Android privacy benchmark with $runner..."
    $testOutput = Invoke-AdbText -Arguments $instrumentArguments
    $testOutput | Out-Host
    if ($testOutput -match 'FAILURES!!!|INSTRUMENTATION_FAILED|shortMsg=Process crashed') {
        Stop-WithError "Android privacy benchmark instrumentation reported a failure."
    }
}

function New-ResultDirectory {
    $root = if ([System.IO.Path]::IsPathRooted($OutputRoot)) {
        $OutputRoot
    } else {
        Join-Path $RepoRoot $OutputRoot
    }
    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $destination = Join-Path $root $timestamp
    $suffix = 1
    while (Test-Path -LiteralPath $destination) {
        $destination = Join-Path $root ("{0}-{1:D2}" -f $timestamp, $suffix)
        $suffix += 1
    }
    New-Item -ItemType Directory -Path $destination -Force | Out-Null
    return $destination
}

function Invoke-DirectPull {
    param(
        [string]$RemotePath,
        [string]$LocalPath
    )
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & $script:AdbPath -s $script:Serial pull $RemotePath $LocalPath 2>$null | Out-Host
        $succeeded = $LASTEXITCODE -eq 0
    } finally {
        $ErrorActionPreference = $previousPreference
    }
    return $succeeded -and (Test-Path -LiteralPath $LocalPath)
}

function Invoke-RunAsExport {
    param(
        [string]$Package,
        [string]$RemotePath,
        [string]$LocalPath
    )
    $arguments = @(
        "-s", $script:Serial, "exec-out", "run-as", "--user", "0", $Package,
        "cat", $RemotePath
    )
    $startInfo = @{
        FilePath = $script:AdbPath
        ArgumentList = $arguments
        Wait = $true
        PassThru = $true
        NoNewWindow = $true
        RedirectStandardOutput = $LocalPath
    }
    $process = Start-Process @startInfo
    if ($process.ExitCode -eq 0 -and (Test-Path -LiteralPath $LocalPath)) {
        return (Get-Item -LiteralPath $LocalPath).Length -gt 0
    }
    Remove-Item -LiteralPath $LocalPath -Force -ErrorAction SilentlyContinue
    return $false
}

function Copy-BenchmarkFiles {
    param(
        [string]$Package,
        [string]$Destination
    )

    $fileNames = @("android-privacy-summary.json", "android-privacy-raw.jsonl")
    $roots = @(
        "/storage/emulated/0/Android/data/$Package/files/benchmark_results",
        "/sdcard/Android/data/$Package/files/benchmark_results"
    )
    foreach ($root in $roots) {
        $allPulled = $true
        foreach ($fileName in $fileNames) {
            $localPath = Join-Path $Destination $fileName
            if (-not (Invoke-DirectPull "$root/$fileName" $localPath)) {
                $allPulled = $false
                break
            }
        }
        if ($allPulled) {
            return [pscustomobject]@{ Method = "adb pull"; Source = $root }
        }
        foreach ($fileName in $fileNames) {
            Remove-Item -LiteralPath (Join-Path $Destination $fileName) -Force -ErrorAction SilentlyContinue
        }
    }

    $runAsRoot = "/storage/emulated/0/Android/data/$Package/files/benchmark_results"
    foreach ($fileName in $fileNames) {
        $localPath = Join-Path $Destination $fileName
        if (-not (Invoke-RunAsExport $Package "$runAsRoot/$fileName" $localPath)) {
            Stop-WithError "Could not retrieve $fileName using direct adb pull or run-as for Android user 0."
        }
    }
    return [pscustomobject]@{ Method = "adb exec-out run-as --user 0"; Source = $runAsRoot }
}

function Test-JsonProperty {
    param(
        [object]$Object,
        [string]$Name
    )
    return $null -ne $Object -and $Object.PSObject.Properties.Name -contains $Name
}

function Read-BenchmarkResults {
    param([string]$Destination)

    $summaryPath = Join-Path $Destination "android-privacy-summary.json"
    $rawPath = Join-Path $Destination "android-privacy-raw.jsonl"
    foreach ($path in @($summaryPath, $rawPath)) {
        if (-not (Test-Path -LiteralPath $path)) {
            Stop-WithError "Expected benchmark result file is missing: $path"
        }
    }

    try {
        $summary = Get-Content -LiteralPath $summaryPath -Raw | ConvertFrom-Json
    } catch {
        Stop-WithError "Summary JSON is invalid: $($_.Exception.Message)"
    }

    $requiredSummary = @(
        "sample_count", "mean_ms", "median_ms", "p95_ms", "min_ms", "max_ms",
        "stddev_ms", "success_rate", "failure_rate", "warmups", "device", "api_level", "groups"
    )
    foreach ($field in $requiredSummary) {
        if (-not (Test-JsonProperty $summary $field)) {
            Write-Warning "Summary JSON is missing expected field '$field'."
        }
    }

    $rows = @()
    $lineNumber = 0
    foreach ($line in Get-Content -LiteralPath $rawPath) {
        $lineNumber += 1
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        try {
            $rows += $line | ConvertFrom-Json
        } catch {
            Stop-WithError "Raw JSONL contains invalid JSON on line $lineNumber`: $($_.Exception.Message)"
        }
    }
    if (-not $rows.Count) {
        Stop-WithError "Raw JSONL contains no benchmark samples."
    }

    $requiredRaw = @(
        "fixture_id", "size_category", "format", "success", "total_ms", "failure_category"
    )
    foreach ($field in $requiredRaw) {
        if (-not (Test-JsonProperty $rows[0] $field)) {
            Write-Warning "Raw JSONL samples are missing expected field '$field'."
        }
    }
    if (-not (Test-JsonProperty $rows[0] "intentionally_invalid")) {
        Write-Warning "Raw samples predate the intentionally_invalid marker; invalid_input is used as a compatibility fallback."
    }
    if ((Test-JsonProperty $summary "sample_count") -and [int]$summary.sample_count -ne $rows.Count) {
        Write-Warning "Summary sample_count ($($summary.sample_count)) does not match raw row count ($($rows.Count))."
    }

    return [pscustomobject]@{
        Summary = $summary
        Rows = @($rows)
        SummaryPath = $summaryPath
        RawPath = $rawPath
    }
}

function Get-IntentionallyInvalid {
    param([object]$Row)
    if (Test-JsonProperty $Row "intentionally_invalid") {
        return [bool]$Row.intentionally_invalid
    }
    return (Test-JsonProperty $Row "failure_category") -and $Row.failure_category -eq "invalid_input"
}

function Show-BenchmarkReport {
    param(
        [object]$Results,
        [string]$Destination
    )

    $summary = $Results.Summary
    Write-Host ""
    Write-Host "Android privacy benchmark summary" -ForegroundColor Cyan
    [pscustomobject]@{
        Device = if (Test-JsonProperty $summary "device") { $summary.device } else { "unknown" }
        Api = if (Test-JsonProperty $summary "api_level") { $summary.api_level } else { "unknown" }
        Samples = if (Test-JsonProperty $summary "sample_count") { $summary.sample_count } else { $Results.Rows.Count }
        Warmups = if (Test-JsonProperty $summary "warmups") { $summary.warmups } else { "unknown" }
        MeanMs = if (Test-JsonProperty $summary "mean_ms") { "{0:N2}" -f $summary.mean_ms } else { "n/a" }
        MedianMs = if (Test-JsonProperty $summary "median_ms") { "{0:N2}" -f $summary.median_ms } else { "n/a" }
        P95Ms = if (Test-JsonProperty $summary "p95_ms") { "{0:N2}" -f $summary.p95_ms } else { "n/a" }
        MinMs = if (Test-JsonProperty $summary "min_ms") { "{0:N2}" -f $summary.min_ms } else { "n/a" }
        MaxMs = if (Test-JsonProperty $summary "max_ms") { "{0:N2}" -f $summary.max_ms } else { "n/a" }
        StdDevMs = if (Test-JsonProperty $summary "stddev_ms") { "{0:N2}" -f $summary.stddev_ms } else { "n/a" }
        Success = if (Test-JsonProperty $summary "success_rate") { "{0:P2}" -f $summary.success_rate } else { "n/a" }
        Failure = if (Test-JsonProperty $summary "failure_rate") { "{0:P2}" -f $summary.failure_rate } else { "n/a" }
    } | Format-List | Out-Host

    if ((Test-JsonProperty $summary "groups") -and $summary.groups) {
        Write-Host "Grouped latency" -ForegroundColor Cyan
        $groupRows = foreach ($property in $summary.groups.PSObject.Properties) {
            $group = $property.Value
            [pscustomobject]@{
                Group = $property.Name
                MeanMs = "{0:N2}" -f $group.mean_ms
                MedianMs = "{0:N2}" -f $group.median_ms
                P95Ms = "{0:N2}" -f $group.p95_ms
                MinMs = "{0:N2}" -f $group.min_ms
                MaxMs = "{0:N2}" -f $group.max_ms
            }
        }
        $groupRows | Format-Table -AutoSize | Out-Host
    }

    $validRows = @($Results.Rows | Where-Object { -not (Get-IntentionallyInvalid $_) })
    $invalidRows = @($Results.Rows | Where-Object { Get-IntentionallyInvalid $_ })
    $validSuccesses = @($validRows | Where-Object { [bool]$_.success }).Count
    $validFailures = $validRows.Count - $validSuccesses
    $invalidRejected = @($invalidRows | Where-Object {
        -not [bool]$_.success -and $_.failure_category -eq "invalid_input"
    }).Count
    $invalidAccepted = @($invalidRows | Where-Object { [bool]$_.success }).Count
    $invalidUnexpectedFailure = $invalidRows.Count - $invalidRejected - $invalidAccepted
    $unexpectedFailures = $validFailures + $invalidUnexpectedFailure
    $validRate = if ($validRows.Count) { $validSuccesses / $validRows.Count } else { 0.0 }
    $rejectionRate = if ($invalidRows.Count) { $invalidRejected / $invalidRows.Count } else { 0.0 }
    $unexpectedRate = if ($Results.Rows.Count) { $unexpectedFailures / $Results.Rows.Count } else { 0.0 }

    Write-Host "Fixture outcome analysis" -ForegroundColor Cyan
    [pscustomobject]@{
        ValidSamples = $validRows.Count
        ValidProcessed = $validSuccesses
        ValidSuccessRate = "{0:P2}" -f $validRate
        InvalidSamples = $invalidRows.Count
        InvalidCorrectlyRejected = $invalidRejected
        InvalidRejectionRate = "{0:P2}" -f $rejectionRate
        InvalidUnexpectedlyAccepted = $invalidAccepted
        UnexpectedFailures = $unexpectedFailures
        UnexpectedFailureRate = "{0:P2}" -f $unexpectedRate
    } | Format-List | Out-Host

    Write-Host "Results saved to: $Destination"
}

function Write-EnvironmentMetadata {
    param(
        [string]$Package,
        [object]$Retrieval,
        [object]$Results,
        [string]$Destination
    )

    $gitCommit = (& git -C $RepoRoot rev-parse HEAD 2>$null | Select-Object -First 1)
    $currentUser = Invoke-AdbText -Arguments @("shell", "am", "get-current-user") -AllowFailure
    $metadata = [ordered]@{
        retrieved_at_utc = (Get-Date).ToUniversalTime().ToString("o")
        retrieved_at_local = (Get-Date).ToString("o")
        git_commit = if ($gitCommit) { "$gitCommit".Trim() } else { $null }
        adb_path = $script:AdbPath
        device_serial = $script:Serial
        device_model = Invoke-AdbText -Arguments @("shell", "getprop", "ro.product.model") -AllowFailure
        android_version = Invoke-AdbText -Arguments @("shell", "getprop", "ro.build.version.release") -AllowFailure
        api_level = Invoke-AdbText -Arguments @("shell", "getprop", "ro.build.version.sdk") -AllowFailure
        active_android_user = "$currentUser".Trim()
        retrieval_android_user = 0
        application_id = $Package
        retrieval_method = $Retrieval.Method
        remote_source_paths = @(
            "$($Retrieval.Source)/android-privacy-summary.json",
            "$($Retrieval.Source)/android-privacy-raw.jsonl"
        )
        local_destination_paths = @($Results.SummaryPath, $Results.RawPath)
        destination = $Destination
        benchmark_requested_by_script = [bool]$RunBenchmark
        requested_warmups = $Warmups
        requested_repetitions = if ($null -ne $Repetitions) { $Repetitions } else { $null }
        fixture_directory = $FixtureDirectory
    }
    $metadataPath = Join-Path $Destination "environment-metadata.json"
    $metadata | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $metadataPath -Encoding UTF8
    return $metadataPath
}

Initialize-Device
$activeUser = Invoke-AdbText -Arguments @("shell", "am", "get-current-user") -AllowFailure
Write-Host "Active Android user: $activeUser; retrieval is pinned to user 0."
if ($RunBenchmark) {
    Invoke-Benchmark
}
$applicationId = Find-ApplicationId
$resultDirectory = New-ResultDirectory
$retrieval = Copy-BenchmarkFiles $applicationId $resultDirectory
$results = Read-BenchmarkResults $resultDirectory
$metadataPath = Write-EnvironmentMetadata $applicationId $retrieval $results $resultDirectory
Write-Host "Environment metadata: $metadataPath"
Show-BenchmarkReport $results $resultDirectory
