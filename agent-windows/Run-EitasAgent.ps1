$ErrorActionPreference = "Stop"

$Root = "C:\EnterpriseIT\agent-windows"
Set-Location $Root

. (Join-Path $Root "modules\EitasConfig.ps1")
. (Join-Path $Root "modules\EitasApi.ps1")

$Config = Get-EitasAgentConfig
$Mode = "Production"

Send-EitasWorkerHeartbeat `
    -Config $Config `
    -WorkerId "lifecycle-agent" `
    -WorkerName "Employee Lifecycle Agent" `
    -Role "lifecycle" `
    -Status "running" `
    -Mode $Mode `
    -StaleAfterSeconds 600 `
    -Details @{ script = "Run-EitasAgent.ps1"; phase = "startup" } | Out-Null

try {
    .\Invoke-EmployeeLifecycleAgent.ps1 -Mode $Mode

    Send-EitasWorkerHeartbeat `
        -Config $Config `
        -WorkerId "lifecycle-agent" `
        -WorkerName "Employee Lifecycle Agent" `
        -Role "lifecycle" `
        -Status "idle" `
        -Mode $Mode `
        -StaleAfterSeconds 600 `
        -Details @{ script = "Run-EitasAgent.ps1"; phase = "completed"; success = $true } | Out-Null
}
catch {
    Send-EitasWorkerHeartbeat `
        -Config $Config `
        -WorkerId "lifecycle-agent" `
        -WorkerName "Employee Lifecycle Agent" `
        -Role "lifecycle" `
        -Status "error" `
        -Mode $Mode `
        -StaleAfterSeconds 600 `
        -Details @{ script = "Run-EitasAgent.ps1"; phase = "error"; error = $_.Exception.Message } | Out-Null

    throw
}
