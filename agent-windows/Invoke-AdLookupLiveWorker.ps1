$ErrorActionPreference = "Continue"

$AgentFolder = "C:\EnterpriseIT\agent-windows"
$AgentScript = Join-Path $AgentFolder "Invoke-EmployeeLifecycleAgent.ps1"
$LogFile = Join-Path $AgentFolder "ad-lookup-live-worker.log"
$IntervalSeconds = 1

Set-Location $AgentFolder

"[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] EITAS AD Lookup Live Worker started in lookup-only mode" | Out-File -FilePath $LogFile -Append -Encoding UTF8

while ($true) {
    try {
        $start = Get-Date

        "[$($start.ToString('yyyy-MM-dd HH:mm:ss'))] Tick lookup-only" | Out-File -FilePath $LogFile -Append -Encoding UTF8

        powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "`$env:EITAS_LOOKUP_ONLY='1'; & '$AgentScript'" 2>&1 |
            Select-String -Pattern "Jobs recherche AD|RECHERCHE AD JOB|UTILISATEUR AD|Resultat recherche AD|explorateur AD|Exploration AD|AD Explorer|lookup-only|ERREUR|WARNING" |
            ForEach-Object {
                "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $($_.Line)" | Out-File -FilePath $LogFile -Append -Encoding UTF8
            }
    }
    catch {
        "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] ERROR $($_.Exception.Message)" | Out-File -FilePath $LogFile -Append -Encoding UTF8
    }

    Start-Sleep -Seconds $IntervalSeconds
}


