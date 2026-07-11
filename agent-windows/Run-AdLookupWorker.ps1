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
. (Join-Path $Root "modules\EitasAdLookup.ps1")

$Config = Get-EitasAgentConfig
$AgentName = Get-EitasAgentName -Config $Config
$NextHeartbeat = Get-Date

Write-EitasLog -Name "ad-lookup-worker-light.log" -Level "OK" -Message "EITAS AD Lookup/Explorer Worker léger démarré sur $AgentName" -Console

while ($true) {
    try {
        $Now = Get-Date
        $SilentWhenEmpty = $true

        if ($Now -ge $NextHeartbeat) {
            Write-EitasLog -Name "ad-lookup-worker-light.log" -Level "INFO" -Message "Worker AD Lookup/Explorer actif, attente de jobs."
            $NextHeartbeat = $Now.AddSeconds($HeartbeatSeconds)
            $SilentWhenEmpty = $false
        }

        Process-EitasPendingAdLookupJobs -Config $Config -SilentWhenEmpty:$SilentWhenEmpty | Out-Null
        Process-EitasPendingAdExplorerJobs -Config $Config -SilentWhenEmpty:$SilentWhenEmpty | Out-Null
    }
    catch {
        Write-EitasLog -Name "ad-lookup-worker-light.log" -Level "ERROR" -Message "Erreur boucle worker AD Lookup/Explorer : $($_.Exception.Message)" -Console
    }

    if ($Once) {
        break
    }

    Start-Sleep -Seconds $IntervalSeconds
}
