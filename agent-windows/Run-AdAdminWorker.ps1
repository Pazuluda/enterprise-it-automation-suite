param(
    [switch]$Once,
    [int]$IntervalSeconds = 1,
    [int]$HeartbeatSeconds = 60
)

$ErrorActionPreference = "Continue"

$Root = $PSScriptRoot
Set-Location $Root

. (Join-Path $Root "modules\EitasConfig.ps1")
. (Join-Path $Root "modules\EitasLogging.ps1")
. (Join-Path $Root "modules\EitasApi.ps1")
. (Join-Path $Root "modules\EitasActiveDirectory.ps1")
. (Join-Path $Root "modules\EitasAdAdmin.ps1")

$Config = Get-EitasAgentConfig
$AgentName = Get-EitasAgentName -Config $Config
$Mode = Get-EitasResolvedAgentMode -Config $Config
$NextHeartbeat = Get-Date
Send-EitasWorkerHeartbeat -Config $Config -WorkerId "ad-admin-worker" -WorkerName "AD Admin Worker" -Role "ad-admin" -Status "running" -Mode $Mode -StaleAfterSeconds 180 -Details @{ script = "Run-AdAdminWorker.ps1"; phase = "startup" } | Out-Null

Write-EitasLog -Name "ad-admin-worker-light.log" -Level "OK" -Message "EITAS AD Admin Worker léger démarré sur $AgentName" -Console

while ($true) {
    try {
        $Now = Get-Date
        $SilentWhenEmpty = $true

        if ($Now -ge $NextHeartbeat) {
            Write-EitasLog -Name "ad-admin-worker-light.log" -Level "INFO" -Message "Worker AD Admin actif, attente de jobs."
            $NextHeartbeat = $Now.AddSeconds($HeartbeatSeconds)
            $Mode = Get-EitasResolvedAgentMode -Config $Config
            Send-EitasWorkerHeartbeat -Config $Config -WorkerId "ad-admin-worker" -WorkerName "AD Admin Worker" -Role "ad-admin" -Status "running" -Mode $Mode -StaleAfterSeconds 180 -Details @{ script = "Run-AdAdminWorker.ps1"; phase = "loop" } | Out-Null
            $SilentWhenEmpty = $false
        }

        Process-EitasPendingAdAdminJobs -Config $Config -SilentWhenEmpty:$SilentWhenEmpty | Out-Null
    }
    catch {
        Write-EitasLog -Name "ad-admin-worker-light.log" -Level "ERROR" -Message "Erreur boucle worker AD Admin : $($_.Exception.Message)" -Console
    }

    if ($Once) {
        break
    }

    Start-Sleep -Seconds $IntervalSeconds
}



