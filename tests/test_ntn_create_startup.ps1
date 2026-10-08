#Requires -Version 7.0
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$scriptPath = Join-Path (Split-Path -Parent $PSScriptRoot) "scripts\ntn-create.ps1"
$tokens = $null
$parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($scriptPath, [ref] $tokens, [ref] $parseErrors)
if ($parseErrors.Count) { throw ($parseErrors -join "`n") }
foreach ($name in @("Test-ConnectionRefused", "Get-EpisodeServerConfig")) {
    $definition = $ast.Find({
        param($node)
        $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq $name
    }, $false)
    . ([scriptblock]::Create($definition.Extent.Text))
}

function Assert-True {
    param([bool] $Condition, [string] $Message)
    if (-not $Condition) { throw $Message }
}

function Reset-Mocks {
    $script:requests = 0
    $script:readyAfter = 1
    $script:existing = $true
    $script:dockerAvailable = $true
    $script:failCommand = ""
    $script:requestError = $null
    $script:commands = [System.Collections.Generic.List[string]]::new()
}

function Invoke-WebRequest {
    param($Uri, $TimeoutSec)
    $script:requests++
    if ($script:requestError) { throw $script:requestError }
    if ($script:requests -lt $script:readyAfter) {
        $socket = [System.Net.Sockets.SocketException]::new(10061)
        throw [System.Net.Http.HttpRequestException]::new("Connection refused", $socket)
    }
    return @{ Content = '{"dependencies":[{"api_name":"create_episode"}]}' }
}

function Get-Command {
    param($Name, $ErrorAction)
    if ($script:dockerAvailable) { return @{ Name = "docker" } }
}

function docker {
    $command = $args -join " "
    $script:commands.Add($command)
    $global:LASTEXITCODE = 0
    if ($args[0] -eq "compose") {
        Assert-True ($command.Contains("--ansi never") -and $command.Contains("--progress plain") -and
            $args -contains "--yes") "Compose startup must not require an interactive console."
    }
    if ($script:failCommand -and $command.StartsWith($script:failCommand)) {
        $global:LASTEXITCODE = 1
        return
    }
    if ($args[0] -eq "container" -and $script:existing) { return "ntn-podcast-creator" }
}

function Get-TestConfig {
    param([bool] $AutoStart = $true, [int] $Timeout = 5)
    Get-EpisodeServerConfig -BaseUrl "http://localhost:7860" -AutoStart $AutoStart `
        -RepositoryRoot (Split-Path -Parent $PSScriptRoot) -TimeoutSeconds $Timeout
}

function Assert-Failure {
    param([scriptblock] $Action, [string] $Expected)
    $message = ""
    try { & $Action | Out-Null } catch { $message = $_.Exception.Message }
    Assert-True ($message.Contains($Expected)) "Expected '$Expected', got '$message'"
}

Reset-Mocks
$config = Get-TestConfig
Assert-True ($config.dependencies[0].api_name -eq "create_episode") "Config was not returned."
Assert-True ($script:commands.Count -eq 0) "Reachable server must not invoke Docker."

Reset-Mocks
$script:readyAfter = 3
$config = Get-TestConfig
Assert-True ($script:requests -eq 3) "Must wait for readiness before returning."
Assert-True ($script:commands -contains "start ntn-podcast-creator") "Existing container was not started."
Assert-True (-not ($script:commands | Where-Object { $_.StartsWith("compose") })) "Existing container must not be recreated."

Reset-Mocks
$script:readyAfter = 2
$script:existing = $false
$null = Get-TestConfig
$compose = @($script:commands | Where-Object { $_.StartsWith("compose") })
Assert-True ($compose.Count -eq 1 -and $compose[0].EndsWith("up -d --no-recreate --yes")) "Missing container must use Compose."
Assert-True ($compose[0].Contains((Join-Path (Split-Path -Parent $PSScriptRoot) "deployment\docker-compose.yml"))) "Compose path must be repository-relative."

Reset-Mocks
$script:readyAfter = 2
Assert-Failure { Get-TestConfig -AutoStart $false } "No NTN server is listening"
Assert-True ($script:commands.Count -eq 0) "Disabled startup must not invoke Docker."

Reset-Mocks
$script:readyAfter = 2
$script:dockerAvailable = $false
Assert-Failure { Get-TestConfig } "Docker is required"

foreach ($failure in @(
    @{ Command = "info"; Message = "Start Docker Desktop" },
    @{ Command = "container"; Message = "Could not list Docker containers" },
    @{ Command = "start"; Message = "Docker startup failed" },
    @{ Command = "compose"; Message = "Docker startup failed" }
)) {
    Reset-Mocks
    $script:readyAfter = 2
    $script:failCommand = $failure.Command
    $script:existing = $failure.Command -ne "compose"
    Assert-Failure { Get-TestConfig } $failure.Message
    Assert-True ($script:requests -eq 1) "Failed Docker commands must stop before readiness/upload."
}

Reset-Mocks
$script:readyAfter = 100
Assert-Failure { Get-TestConfig -Timeout 1 } "did not become ready"

Reset-Mocks
$script:requestError = [System.InvalidOperationException]::new("HTTP 401 Unauthorized")
Assert-Failure { Get-TestConfig } "HTTP 401 Unauthorized"
Assert-True ($script:commands.Count -eq 0) "Non-connection errors must not invoke Docker."

Assert-True (-not (Test-ConnectionRefused ([System.Exception]::new("Other error")))) "Other errors must not count as connection refusal."

$localAssignment = $ast.Find({
    param($node)
    $node -is [System.Management.Automation.Language.AssignmentStatementAst] -and
        $node.Left.Extent.Text -eq '$localDefault'
}, $true)
foreach ($case in @(
    @{ Url = "http://localhost:7860"; Expected = $true },
    @{ Url = "http://127.0.0.1:7860/"; Expected = $true },
    @{ Url = "http://localhost:8080"; Expected = $false },
    @{ Url = "http://example.com:7860"; Expected = $false },
    @{ Url = "https://localhost:7860"; Expected = $false },
    @{ Url = "http://localhost:7860/prefix"; Expected = $false }
)) {
    $server = [Uri] $case.Url
    . ([scriptblock]::Create($localAssignment.Extent.Text))
    Assert-True ($localDefault -eq $case.Expected) "Unexpected auto-start eligibility for $($case.Url)"
}

$listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
$listener.Start()
$port = $listener.LocalEndpoint.Port
$listener.Stop()
$recording = Join-Path ([System.IO.Path]::GetTempPath()) "ntn-startup-test-$([Guid]::NewGuid()).m4a"
try {
    [System.IO.File]::WriteAllBytes($recording, [byte[]] @(1))
    $output = & (Join-Path $PSHOME "pwsh.exe") -NoProfile -File $scriptPath $recording `
        -ServerUrl "http://127.0.0.1:$port" 2>&1 | Out-String
    Assert-True ($LASTEXITCODE -eq 1) "Connection failure must return exit code 1."
    Assert-True ($output.Contains("No NTN server is listening")) "Real connection refusal did not produce startup guidance: $output"
    Assert-True (-not $output.Contains("Starting NTN") -and -not $output.Contains("Uploading")) "Custom URL must not start Docker or upload."
} finally {
    Remove-Item -LiteralPath $recording -Force
}
Write-Host "PASS: startup scenarios, 6 URL eligibility checks, and real refused-connection CLI check; no real Docker containers or recordings were used."
