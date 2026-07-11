param(
    [switch]$Once,
    [int]$IntervalSeconds = 5,
    [int]$HeartbeatSeconds = 60
)

$ErrorActionPreference = "Continue"

$Root = $PSScriptRoot
Set-Location $Root

. (Join-Path $Root "modules\EitasConfig.ps1")
. (Join-Path $Root "modules\EitasLogging.ps1")
. (Join-Path $Root "modules\EitasApi.ps1")
. (Join-Path $Root "modules\EitasActiveDirectory.ps1")

$Config = Get-EitasAgentConfig
$AgentName = Get-EitasAgentName -Config $Config

try {
    $ModeResponse = Get-EitasAgentMode -Config $Config
    $Mode = [string]$ModeResponse.mode
}
catch {
    $Mode = [string]$Config.Mode
}

if ([string]::IsNullOrWhiteSpace($Mode)) {
    $Mode = "Simulation"
}

. (Join-Path $Root "modules\EitasAdCheck.ps1")

$NextHeartbeat = Get-Date

Write-EitasLog -Name "ad-check-worker-light.log" -Level "OK" -Message "EITAS AD Check Worker léger démarré sur $AgentName en mode $Mode" -Console

while ($true) {
    try {
        $Now = Get-Date

        if ($Now -ge $NextHeartbeat) {
            Write-EitasLog -Name "ad-check-worker-light.log" -Level "INFO" -Message "Worker AD Check actif, attente de jobs."
            $NextHeartbeat = $Now.AddSeconds($HeartbeatSeconds)
        }

        Process-PendingAdCheckJobs
    }
    catch {
        Write-EitasLog -Name "ad-check-worker-light.log" -Level "ERROR" -Message "Erreur boucle worker AD Check : $($_.Exception.Message)" -Console
    }

    if ($Once) {
        break
    }

    Start-Sleep -Seconds $IntervalSeconds
}
