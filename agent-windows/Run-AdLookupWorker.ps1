param(
    [switch]$Once,
    [int]$IntervalMilliseconds = 250,
    [int]$IntervalSeconds = 0,
    [int]$SnapshotIntervalSeconds = 5,
    [int]$DomainCatalogIntervalSeconds = 15,
    [int]$HeartbeatSeconds = 60
)

$ErrorActionPreference = "Continue"

$Root = $PSScriptRoot
Set-Location $Root

$SleepMilliseconds = [Math]::Max(
    100,
    $IntervalMilliseconds
)

if ($IntervalSeconds -gt 0) {
    $SleepMilliseconds = [Math]::Max(
        100,
        $IntervalSeconds * 1000
    )
}

. (Join-Path $Root "modules\EitasConfig.ps1")
. (Join-Path $Root "modules\EitasLogging.ps1")
. (Join-Path $Root "modules\EitasApi.ps1")
. (Join-Path $Root "modules\EitasActiveDirectory.ps1")
. (Join-Path $Root "modules\EitasAdLookup.ps1")
. (Join-Path $Root "modules\EitasAdSnapshot.ps1")

$Config = Get-EitasAgentConfig
$AgentName = Get-EitasAgentName -Config $Config
$Mode = Get-EitasResolvedAgentMode -Config $Config
$NextHeartbeat = Get-Date
$NextSnapshot = Get-Date
$LastSnapshotCount = $null
$NextDomainCatalog = Get-Date
$LastDomainCatalogCount = $null
Send-EitasWorkerHeartbeat -Config $Config -WorkerId "ad-lookup-worker" -WorkerName "AD Lookup Explorer Worker" -Role "ad-read" -Status "running" -Mode $Mode -StaleAfterSeconds 180 -Details @{ script = "Run-AdLookupWorker.ps1"; phase = "startup" } | Out-Null

Write-EitasLog -Name "ad-lookup-worker-light.log" -Level "OK" -Message "EITAS AD Lookup/Explorer Worker léger démarré sur $AgentName" -Console

while ($true) {
    try {
        $Now = Get-Date
        $SilentWhenEmpty = $true

        if ($Now -ge $NextSnapshot) {
            try {
                $SnapshotResult = Publish-EitasAdSnapshot `
                    -Config $Config

                if (
                    $null -eq $LastSnapshotCount -or
                    $LastSnapshotCount -ne $SnapshotResult.count
                ) {
                    Write-EitasLog `
                        -Name "ad-lookup-worker-light.log" `
                        -Level "OK" `
                        -Message (
                            "Snapshot AD publie : {0} objet(s) en {1} ms" `
                                -f $SnapshotResult.count,
                                   $SnapshotResult.build_milliseconds
                        ) `
                        -Console
                }

                $LastSnapshotCount = $SnapshotResult.count
            }
            catch {
                Write-EitasLog `
                    -Name "ad-lookup-worker-light.log" `
                    -Level "ERROR" `
                    -Message (
                        "Echec publication snapshot AD : {0}" `
                            -f $_.Exception.Message
                    ) `
                    -Console
            }

            $SnapshotDelay = [Math]::Max(
                2,
                $SnapshotIntervalSeconds
            )

            $NextSnapshot = (
                Get-Date
            ).AddSeconds(
                $SnapshotDelay
            )
        }

        if ($Now -ge $NextDomainCatalog) {
            try {
                $DomainCatalogResult = Publish-EitasAdDomainCatalog `
                    -Config $Config

                if (
                    $null -eq $LastDomainCatalogCount -or
                    $LastDomainCatalogCount -ne $DomainCatalogResult.count
                ) {
                    Write-EitasLog `
                        -Name "ad-lookup-worker-light.log" `
                        -Level "OK" `
                        -Message (
                            "Catalogue domaine publie : {0} objet(s) en {1} ms" `
                                -f $DomainCatalogResult.count,
                                   $DomainCatalogResult.build_milliseconds
                        ) `
                        -Console
                }

                $LastDomainCatalogCount = (
                    $DomainCatalogResult.count
                )
            }
            catch {
                Write-EitasLog `
                    -Name "ad-lookup-worker-light.log" `
                    -Level "ERROR" `
                    -Message (
                        "Echec publication catalogue domaine : {0}" `
                            -f $_.Exception.Message
                    ) `
                    -Console
            }

            $DomainCatalogDelay = [Math]::Max(
                5,
                $DomainCatalogIntervalSeconds
            )

            $NextDomainCatalog = (
                Get-Date
            ).AddSeconds(
                $DomainCatalogDelay
            )
        }


        if ($Now -ge $NextHeartbeat) {
            Write-EitasLog -Name "ad-lookup-worker-light.log" -Level "INFO" -Message "Worker AD Lookup/Explorer actif, attente de jobs."
            $NextHeartbeat = $Now.AddSeconds($HeartbeatSeconds)
            $Mode = Get-EitasResolvedAgentMode -Config $Config
            Send-EitasWorkerHeartbeat -Config $Config -WorkerId "ad-lookup-worker" -WorkerName "AD Lookup Explorer Worker" -Role "ad-read" -Status "running" -Mode $Mode -StaleAfterSeconds 180 -Details @{ script = "Run-AdLookupWorker.ps1"; phase = "loop" } | Out-Null
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

    Start-Sleep -Milliseconds $SleepMilliseconds
}



