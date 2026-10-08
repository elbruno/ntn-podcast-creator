#Requires -Version 7.0
<#
.SYNOPSIS
Start the local NTN container if needed, upload a recording, and download the episode.
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
    [string] $OutputDirectory = ".",
    [switch] $NoAutoStart,
    [ValidateRange(1, 3600)]
    [int] $StartupTimeoutSeconds = 180
)

function Test-ConnectionRefused {
    param([System.Exception] $Exception)

    while ($null -ne $Exception) {
        if ($Exception -is [System.Net.Sockets.SocketException] -and
            $Exception.SocketErrorCode -eq [System.Net.Sockets.SocketError]::ConnectionRefused) {
            return $true
        }
        $Exception = $Exception.InnerException
    }
    return $false
}

function Get-EpisodeServerConfig {
    param(
        [string] $BaseUrl,
        [bool] $AutoStart,
        [string] $RepositoryRoot,
        [int] $TimeoutSeconds
    )

    try {
        $configResponse = Invoke-WebRequest -Uri "$BaseUrl/config" -TimeoutSec 15
    } catch {
        if (-not (Test-ConnectionRefused $_.Exception)) { throw }
        if (-not $AutoStart) {
            throw "No NTN server is listening at $BaseUrl. Start the application first, or use the default local URL without -NoAutoStart to start Docker automatically."
        }
        if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
            throw "Docker is required for automatic startup. Install/start Docker Desktop, or start the application yourself and use -NoAutoStart."
        }
        $composeFile = Join-Path $RepositoryRoot "deployment\docker-compose.yml"
        if (-not (Test-Path -LiteralPath $composeFile -PathType Leaf)) {
            throw "Cannot find the Docker Compose configuration: $composeFile"
        }
        & docker info --format '{{.ServerVersion}}' | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "Docker is not available. Start Docker Desktop, wait until its engine is ready, and rerun this command."
        }
        $containers = @(& docker container ls --all --filter 'name=^/ntn-podcast-creator$' --format '{{.Names}}')
        if ($LASTEXITCODE -ne 0) { throw "Could not list Docker containers." }
        if ($containers -contains "ntn-podcast-creator") {
            Write-Host "Starting existing NTN container (saved settings unchanged)..."
            & docker start ntn-podcast-creator | Out-Host
        } else {
            Write-Host "Starting NTN with Docker Compose (the first run may build the image)..."
            & docker compose --ansi never --progress plain -f $composeFile up -d --no-recreate --yes | Out-Host
        }
        if ($LASTEXITCODE -ne 0) {
            throw "Docker startup failed. Review the Docker errors above; no episode was submitted."
        }
        Write-Host "Waiting up to $TimeoutSeconds seconds for $BaseUrl..."
        $timer = [System.Diagnostics.Stopwatch]::StartNew()
        $lastError = ""
        $configResponse = $null
        while ($timer.Elapsed.TotalSeconds -lt $TimeoutSeconds) {
            $remaining = [Math]::Max(1, [int][Math]::Ceiling($TimeoutSeconds - $timer.Elapsed.TotalSeconds))
            try {
                $configResponse = Invoke-WebRequest -Uri "$BaseUrl/config" -TimeoutSec ([Math]::Min(15, $remaining))
                break
            } catch {
                if (-not (Test-ConnectionRefused $_.Exception) -and
                    $_.Exception -isnot [System.Net.Http.HttpRequestException] -and
                    $_.Exception -isnot [System.Threading.Tasks.TaskCanceledException]) { throw }
                $lastError = $_.Exception.Message
            }
            if ($timer.Elapsed.TotalSeconds -lt $TimeoutSeconds) {
                Start-Sleep -Seconds ([Math]::Min(2, $TimeoutSeconds - $timer.Elapsed.TotalSeconds))
            }
        }
        if ($null -eq $configResponse) {
            throw "NTN did not become ready at $BaseUrl within $TimeoutSeconds seconds. Check 'docker logs --tail 100 ntn-podcast-creator' and the port mapping (127.0.0.1:7860:7860). Use -StartupTimeoutSeconds for a slower startup. Last connection error: $lastError"
        }
    }
    return ConvertFrom-Json -InputObject $configResponse.Content -AsHashtable -Depth 100
}

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
    $localDefault = $server.Host -in @("localhost", "127.0.0.1") -and
        $server.Scheme -eq "http" -and $server.Port -eq 7860 -and $server.AbsolutePath -eq "/"
    $config = Get-EpisodeServerConfig -BaseUrl $base -AutoStart ($localDefault -and -not $NoAutoStart) `
        -RepositoryRoot (Split-Path -Parent $PSScriptRoot) -TimeoutSeconds $StartupTimeoutSeconds
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
