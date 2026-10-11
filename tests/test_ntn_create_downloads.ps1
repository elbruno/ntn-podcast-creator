#Requires -Version 7.0
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$scriptPath = Join-Path (Split-Path -Parent $PSScriptRoot) "scripts\ntn-create.ps1"
$root = Join-Path ([System.IO.Path]::GetTempPath()) "ntn-download-test-$([Guid]::NewGuid())"
$recordingFolder = Join-Path $root "recording [579] with spaces"
$customFolder = Join-Path $root "custom downloads"
$null = New-Item -ItemType Directory -Path $recordingFolder -Force
$recording = Join-Path $recordingFolder "Recording.m4a"
[System.IO.File]::WriteAllBytes($recording, [byte[]] @(1, 2, 3))

$probe = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
$probe.Start()
$port = $probe.LocalEndpoint.Port
$probe.Stop()
$url = "http://localhost:$port"
$listener = [System.Net.HttpListener]::new()
$listener.Prefixes.Add("$url/")
$job = $null
try {
    $listener.Start()
    $job = Start-ThreadJob -ArgumentList $listener -ScriptBlock {
        param($listener)
        while ($listener.IsListening) {
            $context = $listener.GetContext()
            $path = $context.Request.Url.AbsolutePath
            $type = "application/json"
            switch ($path) {
                "/config" { $body = '{"dependencies":[{"api_name":"create_episode"}]}' }
                "/gradio_api/upload" {
                    $reader = [System.IO.StreamReader]::new($context.Request.InputStream)
                    $null = $reader.ReadToEnd()
                    $reader.Dispose()
                    $body = '["/uploads/recording.m4a"]'
                }
                "/gradio_api/call/create_episode" { $body = '{"event_id":"test-job"}' }
                "/gradio_api/call/create_episode/test-job" {
                    $type = "text/event-stream"
                    $result = @{
                        schema = "ntn-episode-v1"; state = "complete"; success = $true
                        output_path = "/outputs/ntn579.mp3"; episode_name = "ntn579"; qc_status = "pass"
                        warnings = @(); logs = @()
                        mp3 = @{ orig_name = "ntn579.mp3"; path = "/outputs/ntn579.mp3" }
                        transcript = @{ orig_name = "ntn579_transcript.txt"; path = "/outputs/ntn579_transcript.txt" }
                        quality_report = $null; denoised = $null
                    }
                    $body = "event: complete`ndata: [$($result | ConvertTo-Json -Depth 8 -Compress)]`n`n"
                }
                "/shutdown" { $body = "{}" }
                default {
                    if ($path.StartsWith("/gradio_api/file=")) {
                        $type = "application/octet-stream"
                        $body = "test artifact bytes"
                    } else {
                        $context.Response.StatusCode = 404
                        $body = "{}"
                    }
                }
            }
            $bytes = [System.Text.Encoding]::UTF8.GetBytes($body)
            $context.Response.ContentType = $type
            $context.Response.ContentLength64 = $bytes.Length
            $context.Response.OutputStream.Write($bytes, 0, $bytes.Length)
            $context.Response.Close()
            if ($path -eq "/shutdown") { break }
        }
    }
    foreach ($useCustom in @($false, $true)) {
        $arguments = @("-NoProfile", "-File", $scriptPath, $recording, "-ServerUrl", $url, "-NoPlay")
        $destination = $recordingFolder
        if ($useCustom) {
            $arguments += @("-OutputDirectory", $customFolder)
            $destination = $customFolder
        }
        $output = & (Join-Path $PSHOME "pwsh.exe") @arguments 2>&1 | Out-String
        if ($LASTEXITCODE -ne 0) { throw "Client failed: $output" }
        foreach ($name in @("ntn579.mp3", "ntn579_transcript.txt")) {
            $target = Join-Path $destination $name
            if ([System.IO.File]::ReadAllText($target) -ne "test artifact bytes") {
                throw "Incorrect downloaded artifact: $target"
            }
        }
        if ($output.Contains("Opened in default audio player")) { throw "-NoPlay was ignored." }
        $repeated = & (Join-Path $PSHOME "pwsh.exe") @arguments 2>&1 | Out-String
        if ($LASTEXITCODE -ne 1 -or -not $repeated.Contains("Download already exists")) {
            throw "Existing downloads must not be overwritten: $repeated"
        }
        if ([System.IO.File]::ReadAllText((Join-Path $destination "ntn579.mp3")) -ne "test artifact bytes") {
            throw "Existing MP3 changed."
        }
        if (Get-ChildItem -LiteralPath $destination -Filter "*.part") { throw "Temporary download leaked." }
    }
    if ([Convert]::ToHexString([System.IO.File]::ReadAllBytes($recording)) -ne "010203") {
        throw "Original recording changed."
    }
    Write-Host "PASS: full HTTP client downloads beside recording or to explicit destination, companion files, -NoPlay, collision safety, and recording preservation."
} finally {
    if ($null -ne $job) {
        $null = Invoke-WebRequest -Uri "$url/shutdown" -TimeoutSec 5
        $null = Wait-Job -Job $job -Timeout 5
        Receive-Job -Job $job -ErrorAction Continue
        Stop-Job -Job $job
        Remove-Job -Job $job
    }
    $listener.Close()
    foreach ($folder in @($recordingFolder, $customFolder)) {
        foreach ($name in @("Recording.m4a", "ntn579.mp3", "ntn579_transcript.txt")) {
            $file = Join-Path $folder $name
            if (Test-Path -LiteralPath $file) { Remove-Item -LiteralPath $file -Force }
        }
        if (Test-Path -LiteralPath $folder) { Remove-Item -LiteralPath $folder }
    }
    Remove-Item -LiteralPath $root
}
