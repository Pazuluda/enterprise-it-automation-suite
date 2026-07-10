function Get-EitasAgentRoot {
    return (Split-Path -Parent $PSScriptRoot)
}

function Get-EitasConfigPath {
    param([string]$Path)

    if (-not [string]::IsNullOrWhiteSpace($Path)) {
        return $Path
    }

    return (Join-Path (Get-EitasAgentRoot) "config.json")
}

function Get-EitasAgentConfig {
    param([string]$Path)

    $ConfigPath = Get-EitasConfigPath -Path $Path

    if (-not (Test-Path $ConfigPath)) {
        throw "Configuration introuvable : $ConfigPath"
    }

    return Get-Content $ConfigPath -Raw | ConvertFrom-Json
}

function Get-EitasApiUrl {
    param([object]$Config)

    if ($null -eq $Config) {
        $Config = Get-EitasAgentConfig
    }

    $ApiUrl = $Config.ApiUrl
    if (-not $ApiUrl) { $ApiUrl = $Config.ApiBaseUrl }
    if (-not $ApiUrl) { $ApiUrl = $Config.BaseUrl }

    if (-not $ApiUrl) {
        throw "ApiUrl manquant dans config.json"
    }

    return ([string]$ApiUrl).TrimEnd("/")
}

function Get-EitasApiKey {
    param([object]$Config)

    if ($null -eq $Config) {
        $Config = Get-EitasAgentConfig
    }

    if (-not $Config.ApiKey) {
        throw "ApiKey manquant dans config.json"
    }

    return [string]$Config.ApiKey
}

function Get-EitasAgentName {
    param([object]$Config)

    if ($null -eq $Config) {
        $Config = Get-EitasAgentConfig
    }

    if ($Config.AgentName) { return [string]$Config.AgentName }
    if ($Config.ComputerName) { return [string]$Config.ComputerName }

    return $env:COMPUTERNAME
}
