$ErrorActionPreference = "Continue"

$AgentDir = "C:\EnterpriseIT\agent-windows"
$LogDir = Join-Path $AgentDir "logs"
$LogFile = Join-Path $LogDir ("agent-{0}.log" -f (Get-Date -Format "yyyy-MM-dd"))

New-Item -ItemType Directory -Path $LogDir -Force | Out-Null

Add-Content -Path $LogFile -Value ""
Add-Content -Path $LogFile -Value ("===== RUN {0} =====" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"))

try {
    Set-Location $AgentDir

    powershell.exe `
        -NoProfile `
        -ExecutionPolicy Bypass `
        -File ".\Invoke-EmployeeLifecycleAgent.ps1" `
        *>> $LogFile
}
catch {
    Add-Content -Path $LogFile -Value ("[ERREUR WRAPPER] {0}" -f $_.Exception.Message)
}
