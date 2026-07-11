. (Join-Path $PSScriptRoot "EitasConfig.ps1")

function Invoke-EitasApiRequest {
    param(
        [string]$Method = "GET",
        [string]$Path,
        [object]$Body,
        [object]$Config
    )

    if ([string]::IsNullOrWhiteSpace($Path)) {
        throw "Path API manquant"
    }

    if ($null -eq $Config) {
        $Config = Get-EitasAgentConfig
    }

    $ApiUrl = Get-EitasApiUrl -Config $Config
    $ApiKey = Get-EitasApiKey -Config $Config

    if (-not $Path.StartsWith("/")) {
        $Path = "/" + $Path
    }

    $Uri = $ApiUrl + $Path

    $Headers = @{
        "X-API-Key" = $ApiKey
    }

    $Params = @{
        Method = $Method
        Uri = $Uri
        Headers = $Headers
        ErrorAction = "Stop"
    }

    if ($null -ne $Body) {
        $JsonBody = $Body | ConvertTo-Json -Depth 50 -Compress
        $Params.ContentType = "application/json; charset=utf-8"
        $Params.Body = [System.Text.Encoding]::UTF8.GetBytes($JsonBody)
    }

    return Invoke-RestMethod @Params
}

function Get-EitasAgentMode {
    param([object]$Config)

    return Invoke-EitasApiRequest -Method "GET" -Path "/api/agent/mode" -Config $Config
}

function Test-EitasApiConnectivity {
    param([object]$Config)

    try {
        $Mode = Get-EitasAgentMode -Config $Config

        return [pscustomobject]@{
            success = $true
            mode = $Mode.mode
            source = $Mode.source
            message = "API joignable"
        }
    }
    catch {
        return [pscustomobject]@{
            success = $false
            mode = $null
            source = $null
            message = $_.Exception.Message
        }
    }
}


function Send-EitasWorkerHeartbeat {
    param(
        [object]$Config,
        [string]$WorkerId,
        [string]$WorkerName,
        [string]$Role,
        [string]$Status = "running",
        [string]$Mode = "",
        [int]$StaleAfterSeconds = 180,
        [object]$Details = @{}
    )

    if ($null -eq $Config) {
        $Config = Get-EitasAgentConfig
    }

    $AgentName = Get-EitasAgentName -Config $Config

    if ([string]::IsNullOrWhiteSpace($WorkerId)) {
        throw "WorkerId manquant"
    }

    if ([string]::IsNullOrWhiteSpace($WorkerName)) {
        $WorkerName = $WorkerId
    }

    if ([string]::IsNullOrWhiteSpace($Role)) {
        $Role = $WorkerId
    }

    $Body = @{
        worker_id = $WorkerId
        worker_name = $WorkerName
        agent_name = $AgentName
        role = $Role
        status = $Status
        mode = $Mode
        pid = $PID
        stale_after_seconds = $StaleAfterSeconds
        details = $Details
    }

    try {
        Invoke-EitasApiRequest `
            -Method "POST" `
            -Path "/api/agent/worker-heartbeat" `
            -Body $Body `
            -Config $Config | Out-Null

        return $true
    }
    catch {
        Write-Warning ("Impossible d'envoyer le heartbeat worker {0} : {1}" -f $WorkerId, $_.Exception.Message)
        return $false
    }
}
