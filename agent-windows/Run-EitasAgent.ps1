$ErrorActionPreference = "Stop"

Set-Location "C:\EnterpriseIT\agent-windows"

.\Invoke-EmployeeLifecycleAgent.ps1 -Mode Production
