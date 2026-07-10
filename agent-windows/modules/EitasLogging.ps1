function Get-EitasLogDirectory {
    $Root = Split-Path -Parent $PSScriptRoot
    $LogDirectory = Join-Path $Root "logs"

    if (-not (Test-Path $LogDirectory)) {
        New-Item -ItemType Directory -Force $LogDirectory | Out-Null
    }

    return $LogDirectory
}

function Get-EitasLogPath {
    param([string]$Name = "eitas-agent.log")

    return (Join-Path (Get-EitasLogDirectory) $Name)
}

function Write-EitasLog {
    param(
        [string]$Message,
        [string]$Level = "INFO",
        [string]$Name = "eitas-agent.log",
        [switch]$Console
    )

    $Line = "[{0}] [{1}] {2}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Level.ToUpper(), $Message
    $Path = Get-EitasLogPath -Name $Name

    $Line | Out-File -FilePath $Path -Append -Encoding UTF8

    if ($Console) {
        if ($Level -eq "ERROR") {
            Write-Host $Line -ForegroundColor Red
        }
        elseif ($Level -eq "WARN") {
            Write-Host $Line -ForegroundColor Yellow
        }
        elseif ($Level -eq "OK") {
            Write-Host $Line -ForegroundColor Green
        }
        else {
            Write-Host $Line
        }
    }
}
