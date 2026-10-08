#Requires -Version 7.0
<#
.SYNOPSIS
Upload one recording to a running NTN container and download the episode.
.EXAMPLE
./scripts/ntn-create.ps1 "C:\Recordings\S recording 3.m4a"
.EXAMPLE
./scripts/ntn-create.ps1 "C:\Recordings\recording.m4a" -Name ntn568 -Transcribe
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory, Position = 0)]
    [string] $Recording,
    [string] $Name = "",
    [switch] $NoBackground,
    [switch] $Transcribe,
    [string] $ServerUrl = "http://localhost:7860",
    [string] $OutputDirectory = "."
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$client = $null
$response = $null
$reader = $null
$submitted = $false
$completed = $false
$temporaryDownload = $null

try {
    $source = Get-Item -LiteralPath $Recording -Force
    if ($source.PSIsContainer -or $source.Length -eq 0) {
        throw "Recording must be a nonempty file."
    }
    $server = [Uri] $ServerUrl.TrimEnd("/")
    if (-not $server.IsAbsoluteUri -or $server.Scheme -notin @("http", "https") -or
        $server.UserInfo -or $server.Query -or $server.Fragment) {
        throw "ServerUrl must be an HTTP(S) server URL without credentials, query, or fragment."
    }
    $base = $server.AbsoluteUri.TrimEnd("/")
    # Gradio's pages map contains an empty key, which requires a JSON hashtable.
    $configResponse = Invoke-WebRequest -Uri "$base/config" -TimeoutSec 15
    $config = ConvertFrom-Json -InputObject $configResponse.Content -AsHashtable -Depth 100
    if (-not ($config["dependencies"] | Where-Object { $_["api_name"] -eq "create_episode" })) {
        throw "This server has no create_episode API. Rebuild/update the container first."
    }
    $null = New-Item -ItemType Directory -Path $OutputDirectory -Force
    $destinationDirectory = (Get-Item -LiteralPath $OutputDirectory).FullName
    Write-Host "Uploading $($source.Name)..."
    $uploadResponse = Invoke-WebRequest -Method Post -Uri "$base/gradio_api/upload" `
        -Form @{ files = $source } -TimeoutSec 300
    $uploaded = @(ConvertFrom-Json -InputObject $uploadResponse.Content)
    if ($uploaded.Count -ne 1 -or $uploaded[0] -isnot [string]) {
        throw "Server returned an invalid upload response."
    }
    $payload = @{
        data = @(
            @{ path = $uploaded[0]; orig_name = $source.Name; meta = @{ _type = "gradio.FileData" } },
            $Name, (-not $NoBackground.IsPresent), $Transcribe.IsPresent
        )
    } | ConvertTo-Json -Depth 8 -Compress
    # An uncertain POST may already have queued a render. Never retry automatically.
    $submitted = $true
    $job = Invoke-RestMethod -Method Post -Uri "$base/gradio_api/call/create_episode" `
        -ContentType "application/json" -Body $payload -TimeoutSec 30
    if (-not $job.event_id -or $job.event_id -notmatch '^[A-Za-z0-9_-]+$') {
        throw "Server returned an invalid job identifier."
    }
    Write-Host "Queued job $($job.event_id). Waiting for processing..."
    $client = [System.Net.Http.HttpClient]::new()
    $client.Timeout = [System.Threading.Timeout]::InfiniteTimeSpan
    $response = $client.GetAsync(
        "$base/gradio_api/call/create_episode/$($job.event_id)",
        [System.Net.Http.HttpCompletionOption]::ResponseHeadersRead
    ).GetAwaiter().GetResult()
    $null = $response.EnsureSuccessStatusCode()
    $stream = $response.Content.ReadAsStreamAsync().GetAwaiter().GetResult()
    $reader = [System.IO.StreamReader]::new($stream)
    $event = ""
    $dataLines = [System.Collections.Generic.List[string]]::new()
    $shown = 0
    $result = $null
    while ($null -ne ($line = $reader.ReadLine())) {
        if ($line.StartsWith("event:")) {
            $event = $line.Substring(6).Trim()
        } elseif ($line.StartsWith("data:")) {
            $dataLines.Add($line.Substring(5).TrimStart())
        } elseif ($line -eq "") {
            if ($event -eq "error") {
                throw "Server job failed: $($dataLines -join "`n")"
            }
            if ($event -in @("generating", "complete")) {
                $values = ConvertFrom-Json -InputObject ($dataLines -join "`n") -Depth 30
                if (@($values).Count -ne 1 -or $values[0].schema -ne "ntn-episode-v1") {
                    throw "Server returned an invalid episode response."
                }
                $snapshot = $values[0]
                if ($snapshot.PSObject.Properties.Name -contains "logs") {
                    for ($i = $shown; $i -lt $snapshot.logs.Count; $i++) {
                        Write-Host $snapshot.logs[$i]
                    }
                    $shown = $snapshot.logs.Count
                }
                if ($event -eq "complete") {
                    $result = $snapshot
                    break
                }
            }
            $event = ""
            $dataLines.Clear()
        }
    }
    if ($null -eq $result) {
        throw "Connection closed before the job's terminal result."
    }
    $completed = $true
    if ($result.state -ne "complete" -or -not $result.success) {
        throw "Episode creation failed: $($result.error)"
    }
    if (-not $result.mp3) {
        throw "Server reported success without an MP3."
    }
    Write-Host "Container output: $($result.output_path)"
    foreach ($kind in @("mp3", "transcript", "quality_report", "denoised")) {
        $artifact = $result.$kind
        if ($null -eq $artifact) { continue }
        $filename = $artifact.orig_name
        if (-not $filename -or $filename -match '[\\/:]' -or $filename -in @(".", "..")) {
            throw "Server returned an unsafe download filename."
        }
        $target = Join-Path $destinationDirectory $filename
        if (Test-Path -LiteralPath $target) {
            throw "Download already exists: $target. Use a different -OutputDirectory."
        }
        $downloadUrl = "$base/gradio_api/file=$([Uri]::EscapeDataString($artifact.path))"
        if ($artifact.PSObject.Properties.Name -contains "url" -and $artifact.url) {
            $downloadUri = [Uri]::new([Uri] "$base/", [string] $artifact.url)
            if ($downloadUri.Authority -ne $server.Authority -or $downloadUri.Scheme -ne $server.Scheme) {
                throw "Server returned a download URL outside the selected server."
            }
            $downloadUrl = $downloadUri.AbsoluteUri
        }
        $temporaryDownload = Join-Path $destinationDirectory ".ntn-$([Guid]::NewGuid()).part"
        Invoke-WebRequest -Uri $downloadUrl -OutFile $temporaryDownload -TimeoutSec 300
        if ((Get-Item -LiteralPath $temporaryDownload -Force).Length -eq 0) {
            throw "Downloaded $kind is empty."
        }
        [System.IO.File]::Move($temporaryDownload, $target, $false)
        $temporaryDownload = $null
        Write-Host "Downloaded: $target"
    }
    foreach ($warning in $result.warnings) { Write-Warning $warning }
    Write-Host "Episode $($result.episode_name) complete. QC: $($result.qc_status)"
} catch {
    Write-Error -Message $_.Exception.Message -ErrorAction Continue
    if ($submitted -and -not $completed) {
        Write-Warning "The server may still be processing. Check container outputs before resubmitting."
    }
    exit 1
} finally {
    if ($null -ne $reader) { $reader.Dispose() }
    if ($null -ne $response) { $response.Dispose() }
    if ($null -ne $client) { $client.Dispose() }
    if ($temporaryDownload -and (Test-Path -LiteralPath $temporaryDownload)) {
        Remove-Item -LiteralPath $temporaryDownload -Force
    }
}
