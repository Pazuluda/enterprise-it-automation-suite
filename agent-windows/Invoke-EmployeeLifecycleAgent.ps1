[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$ErrorActionPreference = "Stop"

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ConfigPath = Join-Path $ScriptRoot "config.json"
$StructureHelperPath = Join-Path $ScriptRoot "Ensure-EitasAdStructure.ps1"

if (-not (Test-Path $ConfigPath)) {
    throw "config.json introuvable dans $ScriptRoot"
}

if (Test-Path $StructureHelperPath) {
    . $StructureHelperPath
}

$Config = Get-Content $ConfigPath -Raw | ConvertFrom-Json

$ApiBaseUrl = [string]$Config.ApiBaseUrl
$ApiKey = [string]$Config.ApiKey
$Mode = [string]$Config.Mode
$AgentName = [string]$Config.AgentName
$TaskName = [string]$Config.TaskName
$Script:AgentIntervalMinutes = $null
$Script:AgentPauseProcessing = $false

if ([string]::IsNullOrWhiteSpace($Mode)) {
    $Mode = "Simulation"
}

if ([string]::IsNullOrWhiteSpace($AgentName)) {
    $AgentName = $env:COMPUTERNAME
}

if ([string]::IsNullOrWhiteSpace($TaskName)) {
    $TaskName = "EITAS Employee Lifecycle Agent"
}

if ([string]::IsNullOrWhiteSpace($ApiBaseUrl)) {
    throw "ApiBaseUrl manquant dans config.json"
}

function Test-EitasDnAllowedFallback {
    param(
        [string]$DistinguishedName,
        [string]$BaseOu
    )

    if ([string]::IsNullOrWhiteSpace($DistinguishedName)) {
        return $false
    }

    if ([string]::IsNullOrWhiteSpace($BaseOu)) {
        return $false
    }

    return $DistinguishedName.ToUpper().EndsWith($BaseOu.ToUpper())
}

function Test-EitasDnSafe {
    param(
        [string]$DistinguishedName
    )

    if (Get-Command Test-EitasDnAllowed -ErrorAction SilentlyContinue) {
        return Test-EitasDnAllowed -DistinguishedName $DistinguishedName -BaseOu $Config.EitasBaseOu
    }

    return Test-EitasDnAllowedFallback -DistinguishedName $DistinguishedName -BaseOu $Config.EitasBaseOu
}

function Invoke-EitasApi {
    param(
        [string]$Method,
        [string]$Path,
        [object]$Body = $null
    )

    $Uri = $ApiBaseUrl.TrimEnd("/") + $Path

    $Headers = @{}

    if (-not [string]::IsNullOrWhiteSpace($ApiKey)) {
        $Headers["X-API-Key"] = $ApiKey
    }

    if ($Method -eq "GET") {
        return Invoke-RestMethod -Uri $Uri -Method Get -Headers $Headers
    }

    $JsonBody = "{}"

    if ($null -ne $Body) {
        $JsonBody = $Body | ConvertTo-Json -Depth 20
    }

    return Invoke-RestMethod `
        -Uri $Uri `
        -Method $Method `
        -Headers $Headers `
        -ContentType "application/json; charset=utf-8" `
        -Body $JsonBody
}



function Get-AgentRemoteConfig {
    try {
        return Invoke-EitasApi -Method "GET" -Path "/api/agent/config"
    }
    catch {
        Write-Warning "Configuration agent distante non récupérée : $($_.Exception.Message)"
        return $null
    }
}

function Set-AgentTaskInterval {
    param(
        [int]$IntervalMinutes
    )

    if ($IntervalMinutes -lt 1 -or $IntervalMinutes -gt 1440) {
        Write-Warning "Fréquence agent ignorée : $IntervalMinutes minute(s)"
        return
    }

    $MarkerPath = Join-Path $ScriptRoot "agent-interval.txt"
    $CurrentInterval = $null

    if (Test-Path $MarkerPath) {
        try {
            $CurrentInterval = [int]((Get-Content $MarkerPath -Raw).Trim())
        }
        catch {
            $CurrentInterval = $null
        }
    }

    if ($CurrentInterval -eq $IntervalMinutes) {
        Write-Host ("[OK] Fréquence déjà appliquée : toutes les {0} minute(s)" -f $IntervalMinutes)
        return
    }

    try {
        Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop | Out-Null

        $Trigger = New-ScheduledTaskTrigger `
            -Once `
            -At (Get-Date).AddMinutes(1) `
            -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes) `
            -RepetitionDuration (New-TimeSpan -Days 3650)

        Set-ScheduledTask -TaskName $TaskName -Trigger $Trigger | Out-Null

        Set-Content -Path $MarkerPath -Value $IntervalMinutes -Encoding UTF8

        Write-Host ("[OK] Fréquence tâche agent appliquée : toutes les {0} minute(s)" -f $IntervalMinutes) -ForegroundColor Green
    }
    catch {
        Write-Warning "Fréquence tâche agent non appliquée : $($_.Exception.Message)"
    }
}

function Sync-AgentRuntimeConfig {
    $RemoteConfig = Get-AgentRemoteConfig

    if ($null -eq $RemoteConfig) {
        return
    }

    if ($RemoteConfig.interval_minutes) {
        $IntervalMinutes = [int]$RemoteConfig.interval_minutes
        $Script:AgentIntervalMinutes = $IntervalMinutes
        Set-AgentTaskInterval -IntervalMinutes $IntervalMinutes
    }

    if ($null -ne $RemoteConfig.pause_processing) {
        $Script:AgentPauseProcessing = [bool]$RemoteConfig.pause_processing
    }
}


function Get-AgentScheduledTaskStatus {
    try {
        $Task = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
        $TaskInfo = Get-ScheduledTaskInfo -TaskName $TaskName -ErrorAction Stop
        $Trigger = $Task.Triggers | Select-Object -First 1

        $RepetitionInterval = $null

        if ($Trigger -and $Trigger.Repetition -and $Trigger.Repetition.Interval) {
            $RepetitionInterval = [string]$Trigger.Repetition.Interval
        }

        return @{
            task_name = $TaskName
            state = [string]$Task.State
            enabled = [bool]$Task.Settings.Enabled
            last_run_time = if ($TaskInfo.LastRunTime) { $TaskInfo.LastRunTime.ToString("s") } else { $null }
            next_run_time = if ($TaskInfo.NextRunTime) { $TaskInfo.NextRunTime.ToString("s") } else { $null }
            last_task_result = $TaskInfo.LastTaskResult
            repetition_interval = $RepetitionInterval
        }
    }
    catch {
        return @{
            task_name = $TaskName
            state = "unknown"
            enabled = $false
            error = $_.Exception.Message
        }
    }
}

function Send-AgentHeartbeat {
    try {
        $Body = @{
            agent_name = $AgentName
            computer_name = $env:COMPUTERNAME
            mode = $Mode
            script = "Invoke-EmployeeLifecycleAgent.ps1"
            status = "running"
            message = "Heartbeat agent reçu"
            api_base_url = $ApiBaseUrl
            version = "0.1.0"
            schedule_interval_minutes = $Script:AgentIntervalMinutes
            pause_processing = $Script:AgentPauseProcessing
            task = Get-AgentScheduledTaskStatus
        }

        Invoke-EitasApi -Method "POST" -Path "/api/agent/heartbeat" -Body $Body | Out-Null

        Write-Host "[OK] Heartbeat agent envoyé"
    }
    catch {
        Write-Warning "Heartbeat agent non envoyé : $($_.Exception.Message)"
    }
}

function Send-AgentResult {
    param(
        [string]$RequestId,
        [bool]$Success,
        [string]$Message,
        [object]$Details
    )

    $Body = @{
        agent_name = $AgentName
        success = $Success
        message = $Message
        details = $Details
    }

    Invoke-EitasApi -Method "POST" -Path "/api/agent/result/$RequestId" -Body $Body | Out-Null
}

function Claim-Request {
    param(
        [string]$RequestId
    )

    $Body = @{
        agent_name = $AgentName
    }

    Invoke-EitasApi -Method "POST" -Path "/api/agent/claim/$RequestId" -Body $Body | Out-Null
}

function New-EitasResult {
    param(
        [bool]$Success,
        [string]$Message,
        [object]$Details
    )

    return @{
        success = $Success
        message = $Message
        details = $Details
    }
}

function Test-ProductionPrerequisites {
    Write-Host ""
    Write-Host "=== PREFLIGHT PRODUCTION AD ===" -ForegroundColor Cyan

    Import-Module ActiveDirectory -ErrorAction Stop
    Write-Host "[OK] Module ActiveDirectory disponible." -ForegroundColor Green

    $ComputerDomain = (Get-CimInstance Win32_ComputerSystem).Domain

    if ([string]::IsNullOrWhiteSpace($ComputerDomain) -or $ComputerDomain -eq "WORKGROUP") {
        throw "Machine non jointe au domaine."
    }

    Write-Host ("[OK] Machine jointe au domaine : {0}" -f $ComputerDomain) -ForegroundColor Green

    $Domain = Get-ADDomain -ErrorAction Stop

    Write-Host ("[OK] Domaine AD joignable : {0}" -f $Domain.DNSRoot) -ForegroundColor Green
    Write-Host ("[INFO] DistinguishedName : {0}" -f $Domain.DistinguishedName)

    if (-not [string]::IsNullOrWhiteSpace([string]$Config.EitasBaseOu)) {
        Get-ADOrganizationalUnit -Identity $Config.EitasBaseOu -ErrorAction Stop | Out-Null
        Write-Host ("[OK] OU EITAS trouvee : {0}" -f $Config.EitasBaseOu) -ForegroundColor Green
    }

    Write-Host "[OK] Preflight Production AD valide." -ForegroundColor Green
}

function Get-RequestType {
    param([object]$Request)

    if (-not [string]::IsNullOrWhiteSpace([string]$Request.type)) {
        return [string]$Request.type
    }

    if (-not [string]::IsNullOrWhiteSpace([string]$Request.request_type)) {
        return [string]$Request.request_type
    }

    return "onboarding"
}

function Invoke-OnboardingSimulation {
    param([object]$Request)

    $Payload = $Request.ad_payload

    Write-Host ""
    Write-Host ("[ONBOARDING SIMULATION] {0}" -f $Payload.display_name) -ForegroundColor Yellow
    Write-Host ("Login  : {0}" -f $Payload.username)
    Write-Host ("Email  : {0}" -f $Payload.email)
    Write-Host ("Service: {0}" -f $Payload.department)
    Write-Host ("Poste  : {0}" -f $Payload.job_title)
    Write-Host ("OU     : {0}" -f $Payload.ou)

    if ($Payload.groups) {
        foreach ($Group in $Payload.groups) {
            Write-Host ("Groupe : {0}" -f $Group)
        }
    }

    Write-Host "[SIMULATION] Creation compte AD non executee." -ForegroundColor Yellow

    return New-EitasResult `
        -Success $true `
        -Message "Onboarding simule termine" `
        -Details @{
            request_type = "onboarding"
            mode = $Mode
            agent = $AgentName
            simulated = $true
            username = $Payload.username
            display_name = $Payload.display_name
            ou = $Payload.ou
            groups = $Payload.groups
        }
}

function New-EitasTemporaryPassword {
    $Chars = "abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    $RandomPart = -join (1..14 | ForEach-Object {
        $Chars[(Get-Random -Minimum 0 -Maximum $Chars.Length)]
    })

    return ("Eitas!{0}9aA" -f $RandomPart)
}

function Invoke-OnboardingProduction {
    param([object]$Request)

    Import-Module ActiveDirectory -ErrorAction Stop

    $Payload = $Request.ad_payload
    $Domain = Get-ADDomain

    $Username = [string]$Payload.username
    $DisplayName = [string]$Payload.display_name
    $Email = [string]$Payload.email
    $Department = [string]$Payload.department
    $JobTitle = [string]$Payload.job_title
    $TargetOu = [string]$Payload.ou

    if ([string]::IsNullOrWhiteSpace($Username)) {
        throw "Username manquant dans la demande."
    }

    if ([string]::IsNullOrWhiteSpace($DisplayName)) {
        throw "Display name manquant dans la demande."
    }

    if ([string]::IsNullOrWhiteSpace($TargetOu)) {
        throw "OU cible manquante dans la demande."
    }

    if (-not (Test-EitasDnSafe -DistinguishedName $TargetOu)) {
        throw "OU cible refusee hors perimetre EITAS : $TargetOu"
    }

    Get-ADOrganizationalUnit -Identity $TargetOu -ErrorAction Stop | Out-Null

    $ExistingUser = $null

    try {
        $ExistingUser = Get-ADUser -Identity $Username -ErrorAction Stop
    }
    catch {
        $ExistingUser = $null
    }

    if ($ExistingUser) {
        throw "Un compte AD existe deja avec ce login : $Username"
    }

    $FirstName = [string]$Payload.first_name
    $LastName = [string]$Payload.last_name

    if ([string]::IsNullOrWhiteSpace($FirstName) -or [string]::IsNullOrWhiteSpace($LastName)) {
        $NameParts = $DisplayName.Split(" ", 2)

        if ([string]::IsNullOrWhiteSpace($FirstName)) {
            $FirstName = $NameParts[0]
        }

        if ([string]::IsNullOrWhiteSpace($LastName)) {
            if ($NameParts.Count -gt 1) {
                $LastName = $NameParts[1]
            }
            else {
                $LastName = $DisplayName
            }
        }
    }

    if ([string]::IsNullOrWhiteSpace($Email)) {
        $Email = ("{0}@{1}" -f $Username, $Domain.DNSRoot.ToLower())
    }

    $InitialPassword = New-EitasTemporaryPassword
    $SecurePassword = ConvertTo-SecureString $InitialPassword -AsPlainText -Force

    Write-Host ""
    Write-Host ("[AD CREATE] {0}" -f $DisplayName) -ForegroundColor Green
    Write-Host ("Login  : {0}" -f $Username)
    Write-Host ("UPN    : {0}" -f $Email)
    Write-Host ("OU     : {0}" -f $TargetOu)
    Write-Host ("Service: {0}" -f $Department)
    Write-Host ("Poste  : {0}" -f $JobTitle)

    New-ADUser `
        -Name $DisplayName `
        -DisplayName $DisplayName `
        -GivenName $FirstName `
        -Surname $LastName `
        -SamAccountName $Username `
        -UserPrincipalName $Email `
        -EmailAddress $Email `
        -Department $Department `
        -Title $JobTitle `
        -Path $TargetOu `
        -AccountPassword $SecurePassword `
        -Enabled $true `
        -ChangePasswordAtLogon $true `
        -ErrorAction Stop

    Write-Host "[OK] Compte AD cree." -ForegroundColor Green
    Write-Host ""
    Write-Host "=== MOT DE PASSE TEMPORAIRE ===" -ForegroundColor Yellow
    Write-Host $InitialPassword -ForegroundColor Yellow
    Write-Host "A conserver maintenant : il ne sera pas envoye dans l API." -ForegroundColor Yellow

    $GroupsAdded = @()

    if ($Payload.groups) {
        foreach ($Group in $Payload.groups) {
            $CleanGroup = [string]$Group

            if ([string]::IsNullOrWhiteSpace($CleanGroup)) {
                continue
            }

            Add-ADGroupMember `
                -Identity $CleanGroup `
                -Members $Username `
                -ErrorAction Stop

            $GroupsAdded += $CleanGroup
            Write-Host ("[OK] Ajoute au groupe : {0}" -f $CleanGroup) -ForegroundColor Green
        }
    }

    return New-EitasResult `
        -Success $true `
        -Message "Onboarding Active Directory termine" `
        -Details @{
            request_type = "onboarding"
            mode = $Mode
            agent = $AgentName
            created = $true
            username = $Username
            email = $Email
            display_name = $DisplayName
            ou = $TargetOu
            groups_added = $GroupsAdded
            password_generated = $true
            password_stored_in_api = $false
        }
}

function Invoke-OffboardingSimulation {
    param([object]$Request)

    $Payload = $Request.ad_payload

    Write-Host ""
    Write-Host ("[OFFBOARDING SIMULATION] {0}" -f $Payload.display_name) -ForegroundColor Yellow
    Write-Host ("Login       : {0}" -f $Payload.username)
    Write-Host ("Move to OU  : {0}" -f $Payload.move_to_ou)
    Write-Host ("Disable     : {0}" -f $Payload.disable_account)
    Write-Host ("Remove group: {0}" -f $Payload.remove_groups)
    Write-Host "[SIMULATION] Offboarding AD non execute." -ForegroundColor Yellow

    return New-EitasResult `
        -Success $true `
        -Message "Offboarding simule termine" `
        -Details @{
            request_type = "offboarding"
            mode = $Mode
            agent = $AgentName
            simulated = $true
            username = $Payload.username
            display_name = $Payload.display_name
            move_to_ou = $Payload.move_to_ou
        }
}

function Invoke-OffboardingProduction {
    param([object]$Request)

    Import-Module ActiveDirectory -ErrorAction Stop

    $Payload = $Request.ad_payload
    $Username = [string]$Payload.username

    if ([string]::IsNullOrWhiteSpace($Username)) {
        throw "Username manquant dans la demande offboarding."
    }

    $MoveToOu = [string]$Payload.move_to_ou

    if ([string]::IsNullOrWhiteSpace($MoveToOu)) {
        $MoveToOu = [string]$Config.DisabledUsersOu
    }

    if ([string]::IsNullOrWhiteSpace($MoveToOu)) {
        $MoveToOu = "OU=Disabled Users,OU=EITAS,DC=API,DC=LOCAL"
    }

    if (-not (Test-EitasDnSafe -DistinguishedName $MoveToOu)) {
        throw "OU offboarding refusee hors perimetre EITAS : $MoveToOu"
    }

    Get-ADOrganizationalUnit -Identity $MoveToOu -ErrorAction Stop | Out-Null

    $User = Get-ADUser `
        -Identity $Username `
        -Properties DisplayName, SamAccountName, UserPrincipalName, DistinguishedName, Enabled, MemberOf `
        -ErrorAction Stop

    if (-not (Test-EitasDnSafe -DistinguishedName $User.DistinguishedName)) {
        throw "Utilisateur refuse hors perimetre EITAS : $($User.DistinguishedName)"
    }

    Write-Host ""
    Write-Host ("[AD OFFBOARDING] {0}" -f $User.DisplayName) -ForegroundColor Magenta
    Write-Host ("Login          : {0}" -f $User.SamAccountName)
    Write-Host ("UPN            : {0}" -f $User.UserPrincipalName)
    Write-Host ("Actuellement   : {0}" -f $User.DistinguishedName)
    Write-Host ("OU cible       : {0}" -f $MoveToOu)
    Write-Host ("Desactiver     : {0}" -f $Payload.disable_account)
    Write-Host ("Retirer groupes: {0}" -f $Payload.remove_groups)

    $GroupsRemoved = @()

    if ($Payload.remove_groups -eq $true) {
        $GroupsOu = [string]$Config.GroupsOu

        if ([string]::IsNullOrWhiteSpace($GroupsOu)) {
            $GroupsOu = "OU=Groups,OU=EITAS,DC=API,DC=LOCAL"
        }

        $GroupsOuUpper = $GroupsOu.ToUpper()

        $Memberships = Get-ADPrincipalGroupMembership -Identity $User.SamAccountName |
            Where-Object {
                ($_.Name -like "GG_*") -or ($_.DistinguishedName.ToUpper().EndsWith("," + $GroupsOuUpper))
            }

        foreach ($Group in $Memberships) {
            Remove-ADGroupMember `
                -Identity $Group.DistinguishedName `
                -Members $User.DistinguishedName `
                -Confirm:$false `
                -ErrorAction Stop

            $GroupsRemoved += $Group.Name
            Write-Host ("[OK] Retire du groupe : {0}" -f $Group.Name) -ForegroundColor Green
        }

        if ($GroupsRemoved.Count -eq 0) {
            Write-Host "[INFO] Aucun groupe EITAS/GG_ a retirer." -ForegroundColor Yellow
        }
    }

    if ($Payload.disable_account -eq $true) {
        Disable-ADAccount -Identity $User.DistinguishedName -ErrorAction Stop
        Write-Host "[OK] Compte desactive." -ForegroundColor Green
    }

    $OffboardingDescription = "Offboarded by EITAS on {0}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss")

    Set-ADUser `
        -Identity $User.DistinguishedName `
        -Description $OffboardingDescription `
        -ErrorAction Stop

    $CurrentParentOu = $User.DistinguishedName.Substring($User.DistinguishedName.IndexOf(",") + 1)

    if ($CurrentParentOu.ToUpper() -ne $MoveToOu.ToUpper()) {
        Move-ADObject `
            -Identity $User.DistinguishedName `
            -TargetPath $MoveToOu `
            -ErrorAction Stop

        Write-Host "[OK] Compte deplace vers OU offboarding." -ForegroundColor Green
    }
    else {
        Write-Host "[INFO] Compte deja dans l OU offboarding." -ForegroundColor Yellow
    }

    if ($Payload.convert_mailbox -eq $true) {
        Write-Host "[SIMULATION] Conversion mailbox demandee, non executee sans Exchange." -ForegroundColor Yellow
    }

    if (-not [string]::IsNullOrWhiteSpace([string]$Payload.forward_to)) {
        Write-Host ("[SIMULATION] Redirection mail demandee vers : {0}" -f $Payload.forward_to) -ForegroundColor Yellow
    }

    return New-EitasResult `
        -Success $true `
        -Message "Offboarding Active Directory termine" `
        -Details @{
            request_type = "offboarding"
            mode = $Mode
            agent = $AgentName
            username = $User.SamAccountName
            display_name = $User.DisplayName
            disabled = [bool]$Payload.disable_account
            moved_to_ou = $MoveToOu
            groups_removed = $GroupsRemoved
            account_reactivated = $AccountReactivated
            mailbox_convert_requested = [bool]$Payload.convert_mailbox
            forward_to = $Payload.forward_to
            mailbox_handled = $false
        }
}


function Get-EitasPayloadValue {
    param(
        [object]$Payload,
        [string[]]$Names
    )

    foreach ($Name in $Names) {
        if ($Payload.PSObject.Properties.Name -contains $Name) {
            $Value = $Payload.PSObject.Properties[$Name].Value

            if ($null -ne $Value -and -not [string]::IsNullOrWhiteSpace([string]$Value)) {
                return [string]$Value
            }
        }
    }

    return ""
}

function Get-EitasPayloadArray {
    param(
        [object]$Payload,
        [string[]]$Names
    )

    $Items = @()

    foreach ($Name in $Names) {
        if ($Payload.PSObject.Properties.Name -contains $Name) {
            $Value = $Payload.PSObject.Properties[$Name].Value

            if ($null -eq $Value) {
                continue
            }

            if ($Value -is [array]) {
                foreach ($Item in $Value) {
                    if (-not [string]::IsNullOrWhiteSpace([string]$Item)) {
                        $Items += [string]$Item
                    }
                }
            }
            else {
                $Text = [string]$Value

                foreach ($Item in ($Text -split "[`r`n,;]+")) {
                    if (-not [string]::IsNullOrWhiteSpace($Item)) {
                        $Items += $Item.Trim()
                    }
                }
            }
        }
    }

    return @($Items | Select-Object -Unique)
}


function Get-EitasPayloadBool {
    param(
        [object]$Payload,
        [string[]]$Names
    )

    foreach ($Name in $Names) {
        if ($Payload.PSObject.Properties.Name -contains $Name) {
            $Value = $Payload.PSObject.Properties[$Name].Value

            if ($Value -eq $true) {
                return $true
            }

            if ($Value -eq $false) {
                return $false
            }

            $Text = ([string]$Value).Trim().ToLower()

            if ($Text -in @("true", "1", "yes", "oui", "on", "enable", "enabled", "reactivate", "reactiver", "réactiver")) {
                return $true
            }
        }
    }

    return $false
}

function Invoke-ModificationProduction {
    param([object]$Request)

    Import-Module ActiveDirectory -ErrorAction Stop

    $Payload = $Request.ad_payload

    $Username = Get-EitasPayloadValue -Payload $Payload -Names @(
        "username",
        "login",
        "sam_account_name",
        "samAccountName"
    )

    if ([string]::IsNullOrWhiteSpace($Username)) {
        throw "Username manquant dans la demande modification."
    }

    $NewDepartment = Get-EitasPayloadValue -Payload $Payload -Names @(
        "new_department",
        "department",
        "target_department",
        "service"
    )

    $NewTitle = Get-EitasPayloadValue -Payload $Payload -Names @(
        "new_job_title",
        "job_title",
        "target_job_title",
        "title",
        "poste"
    )

    $NewOu = Get-EitasPayloadValue -Payload $Payload -Names @(
        "new_ou",
        "target_ou",
        "move_to_ou",
        "ou"
    )

    $NewEmail = Get-EitasPayloadValue -Payload $Payload -Names @(
        "new_email",
        "email"
    )

    $GroupsToAdd = Get-EitasPayloadArray -Payload $Payload -Names @(
        "add_groups",
        "groups_to_add",
        "groups_added"
    )

    $GroupsToRemove = Get-EitasPayloadArray -Payload $Payload -Names @(
        "remove_groups",
        "groups_to_remove",
        "groups_removed"
    )

    $ReactivateAccount = Get-EitasPayloadBool -Payload $Payload -Names @(
        "reactivate_account",
        "enable_account",
        "reactiver_account",
        "reactiver",
        "réactiver"
    )

    $User = Get-ADUser `
        -Identity $Username `
        -Properties DisplayName, SamAccountName, UserPrincipalName, EmailAddress, Department, Title, DistinguishedName, Enabled `
        -ErrorAction Stop

    if (-not (Test-EitasDnSafe -DistinguishedName $User.DistinguishedName)) {
        throw "Utilisateur refuse hors perimetre EITAS : $($User.DistinguishedName)"
    }

    Write-Host ""
    Write-Host ("[AD MODIFICATION] {0}" -f $User.DisplayName) -ForegroundColor Cyan
    Write-Host ("Login        : {0}" -f $User.SamAccountName)
    Write-Host ("Actuellement : {0}" -f $User.DistinguishedName)

    $ChangedFields = @{}

    $SetParams = @{
        Identity = $User.DistinguishedName
        ErrorAction = "Stop"
    }

    if (-not [string]::IsNullOrWhiteSpace($NewDepartment)) {
        $SetParams["Department"] = $NewDepartment
        $ChangedFields["department"] = $NewDepartment
        Write-Host ("Nouveau service : {0}" -f $NewDepartment)
    }

    if (-not [string]::IsNullOrWhiteSpace($NewTitle)) {
        $SetParams["Title"] = $NewTitle
        $ChangedFields["title"] = $NewTitle
        Write-Host ("Nouveau poste   : {0}" -f $NewTitle)
    }

    if (-not [string]::IsNullOrWhiteSpace($NewEmail)) {
        $SetParams["EmailAddress"] = $NewEmail
        $SetParams["UserPrincipalName"] = $NewEmail
        $ChangedFields["email"] = $NewEmail
        Write-Host ("Nouvel email    : {0}" -f $NewEmail)
    }

    if ($SetParams.Keys.Count -gt 2) {
        Set-ADUser @SetParams
        Write-Host "[OK] Attributs utilisateur mis a jour." -ForegroundColor Green
    }
    else {
        Write-Host "[INFO] Aucun attribut utilisateur a modifier." -ForegroundColor Yellow
    }

    $GroupsAdded = @()

    foreach ($Group in $GroupsToAdd) {
        $CleanGroup = [string]$Group

        if ([string]::IsNullOrWhiteSpace($CleanGroup)) {
            continue
        }

        Add-ADGroupMember `
            -Identity $CleanGroup `
            -Members $User.SamAccountName `
            -ErrorAction Stop

        $GroupsAdded += $CleanGroup
        Write-Host ("[OK] Ajoute au groupe : {0}" -f $CleanGroup) -ForegroundColor Green
    }

    $GroupsRemoved = @()

    foreach ($Group in $GroupsToRemove) {
        $CleanGroup = [string]$Group

        if ([string]::IsNullOrWhiteSpace($CleanGroup)) {
            continue
        }

        Remove-ADGroupMember `
            -Identity $CleanGroup `
            -Members $User.SamAccountName `
            -Confirm:$false `
            -ErrorAction Stop

        $GroupsRemoved += $CleanGroup
        Write-Host ("[OK] Retire du groupe : {0}" -f $CleanGroup) -ForegroundColor Green
    }

    $AccountReactivated = $false

    $TargetIsDisabledOu = $false

    if (-not [string]::IsNullOrWhiteSpace($NewOu)) {
        $TargetIsDisabledOu = $NewOu.ToUpper().Contains("OU=DISABLED USERS")
    }

    $ShouldReactivateAccount = ($ReactivateAccount -eq $true)

    if (($User.Enabled -eq $false) -and (-not $TargetIsDisabledOu)) {
        $ShouldReactivateAccount = $true
        Write-Host "[INFO] Compte desactive + OU cible active : reactivation automatique." -ForegroundColor Yellow
    }

    if ($ShouldReactivateAccount -eq $true) {
        Enable-ADAccount -Identity $User.DistinguishedName -ErrorAction Stop

        $ReactivationDescription = "Reactivated by EITAS on {0}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss")

        Set-ADUser `
            -Identity $User.DistinguishedName `
            -Description $ReactivationDescription `
            -ErrorAction Stop

        $ChangedFields["enabled"] = $true
        $ChangedFields["description"] = $ReactivationDescription
        $AccountReactivated = $true

        Write-Host "[OK] Compte reactive." -ForegroundColor Green
    }

    $Moved = $false

    if (-not [string]::IsNullOrWhiteSpace($NewOu)) {
        if (-not (Test-EitasDnSafe -DistinguishedName $NewOu)) {
            throw "OU modification refusee hors perimetre EITAS : $NewOu"
        }

        Get-ADOrganizationalUnit -Identity $NewOu -ErrorAction Stop | Out-Null

        $CurrentParentOu = $User.DistinguishedName.Substring($User.DistinguishedName.IndexOf(",") + 1)

        if ($CurrentParentOu.ToUpper() -ne $NewOu.ToUpper()) {
            Move-ADObject `
                -Identity $User.DistinguishedName `
                -TargetPath $NewOu `
                -ErrorAction Stop

            $Moved = $true
            Write-Host ("[OK] Utilisateur deplace vers : {0}" -f $NewOu) -ForegroundColor Green
        }
        else {
            Write-Host "[INFO] Utilisateur deja dans la bonne OU." -ForegroundColor Yellow
        }
    }
    else {
        Write-Host "[INFO] Aucune OU cible demandee." -ForegroundColor Yellow
    }

    return New-EitasResult `
        -Success $true `
        -Message "Modification Active Directory terminee" `
        -Details @{
            request_type = "modification"
            mode = $Mode
            agent = $AgentName
            username = $User.SamAccountName
            display_name = $User.DisplayName
            changed_fields = $ChangedFields
            moved = $Moved
            target_ou = $NewOu
            groups_added = $GroupsAdded
            groups_removed = $GroupsRemoved
            account_reactivated = $AccountReactivated
        }
}

function Invoke-ModificationSimulation {
    param([object]$Request)

    $Payload = $Request.ad_payload

    Write-Host ""
    Write-Host ("[MODIFICATION SIMULATION] {0}" -f $Payload.display_name) -ForegroundColor Yellow
    Write-Host ("Login : {0}" -f $Payload.username)
    Write-Host "[SIMULATION] Modification AD non executee." -ForegroundColor Yellow

    return New-EitasResult `
        -Success $true `
        -Message "Modification simulee terminee" `
        -Details @{
            request_type = "modification"
            mode = $Mode
            agent = $AgentName
            simulated = $true
            username = $Payload.username
            display_name = $Payload.display_name
        }
}

function Get-PendingRequests {
Sync-AgentRuntimeConfig
Send-AgentHeartbeat

if ($Script:AgentPauseProcessing) {
    Write-Host "[PAUSE] Traitement agent en pause depuis le portail. Heartbeat envoyé, aucune demande traitée." -ForegroundColor Yellow
    return
}

    $Pending = Invoke-EitasApi -Method "GET" -Path "/api/agent/pending"

    if ($null -eq $Pending) {
        return @()
    }

    if ($Pending.requests) {
        return @($Pending.requests)
    }

    if ($Pending.items) {
        return @($Pending.items)
    }

    if ($Pending.id) {
        return @($Pending)
    }

    return @()
}

Write-Host ""
# STEP166_AGENT_MODE_FROM_PORTAL_FUNCTION
function Sync-AgentModeFromPortal {
    try {
        $ModeResponse = Invoke-EitasApi -Method "GET" -Path "/api/agent/mode"

        if ($null -eq $ModeResponse -or [string]::IsNullOrWhiteSpace([string]$ModeResponse.mode)) {
            return
        }

        $RemoteMode = [string]$ModeResponse.mode

        if ($RemoteMode -ne "Production" -and $RemoteMode -ne "Simulation") {
            Write-Warning ("Mode portail ignore : {0}" -f $RemoteMode)
            return
        }

        if ($script:Mode -ne $RemoteMode) {
            Write-Host ("[INFO] Mode agent recupere depuis portail : {0}" -f $RemoteMode) -ForegroundColor Cyan
        }

        $script:Mode = $RemoteMode
    }
    catch {
        Write-Warning ("Impossible de recuperer le mode agent depuis le portail : {0}" -f $_.Exception.Message)
    }
}

# STEP222_REMOVED_AD_LOOKUP_FUNCTIONS - déplacé vers modules\EitasAdLookup.ps1


# STEP222_REMOVED_AD_EXPLORER_FUNCTIONS - déplacé vers modules\EitasAdLookup.ps1


# STEP222_REMOVED_AD_ADMIN_FUNCTIONS - déplacé vers modules\EitasAdAdmin.ps1

# STEP222_REMOVED_AD_CHECK_FUNCTIONS - déplacé vers modules\EitasAdCheck.ps1

# STEP166_AGENT_MODE_FROM_PORTAL_CALL
Sync-AgentModeFromPortal

Write-Host "=== EMPLOYEE LIFECYCLE AGENT ===" -ForegroundColor Cyan
Write-Host ("Agent : {0}" -f $AgentName)
Write-Host ("Mode  : {0}" -f $Mode)
Write-Host ("API   : {0}" -f $ApiBaseUrl)

if ($Mode -eq "Production") {
    Test-ProductionPrerequisites
}

# STEP219_SPECIALIZED_WORKERS_REMOVED
# AD Lookup / AD Explorer sont maintenant traités par Run-AdLookupWorker.ps1.
# AD Admin est maintenant traité par Run-AdAdminWorker.ps1.
# Le script Invoke-EmployeeLifecycleAgent.ps1 ne lance plus ces workers spécialisés.

# STEP220_AD_CHECK_WORKER_REMOVED
# AD Check est maintenant traité par Run-AdCheckWorker.ps1.
$Requests = Get-PendingRequests

Write-Host ""
Write-Host ("[INFO] Demandes en attente : {0}" -f $Requests.Count)

foreach ($Request in $Requests) {
    $RequestId = [string]$Request.id
    $RequestType = Get-RequestType -Request $Request

    Write-Host ""
    Write-Host ("=== DEMANDE {0} ===" -f $RequestId) -ForegroundColor Cyan
    Write-Host ("Type : {0}" -f $RequestType)

    try {
        Claim-Request -RequestId $RequestId
        Write-Host "[OK] Demande marquee en processing." -ForegroundColor Green

        if ($Mode -eq "Production") {
            if (Get-Command Ensure-EitasRequestAdStructure -ErrorAction SilentlyContinue) {
                Ensure-EitasRequestAdStructure -Request $Request -Config $Config
            }
        }

        if ($RequestType -eq "offboarding") {
            if ($Mode -eq "Production") {
                $Result = Invoke-OffboardingProduction -Request $Request
            }
            else {
                $Result = Invoke-OffboardingSimulation -Request $Request
            }
        }
        elseif ($RequestType -eq "modification") {
            if ($Mode -eq "Production") {
                $Result = Invoke-ModificationProduction -Request $Request
            }
            else {
                $Result = Invoke-ModificationSimulation -Request $Request
            }
        }
        else {
            if ($Mode -eq "Production") {
                $Result = Invoke-OnboardingProduction -Request $Request
            }
            else {
                $Result = Invoke-OnboardingSimulation -Request $Request
            }
        }

        Send-AgentResult `
            -RequestId $RequestId `
            -Success ([bool]$Result.success) `
            -Message ([string]$Result.message) `
            -Details $Result.details

        Write-Host ("[OK] Resultat envoye : {0}" -f $Result.message) -ForegroundColor Green
    }
    catch {
        $ErrorMessage = $_.Exception.Message

        Write-Host ("[ERREUR] {0}" -f $ErrorMessage) -ForegroundColor Red

        try {
            Send-AgentResult `
                -RequestId $RequestId `
                -Success $false `
                -Message $ErrorMessage `
                -Details @{
                    request_type = $RequestType
                    mode = $Mode
                    agent = $AgentName
                    error = $ErrorMessage
                }

            Write-Host "[OK] Erreur envoyee a l API." -ForegroundColor Yellow
        }
        catch {
            Write-Host ("[ERREUR] Impossible d envoyer le resultat a l API : {0}" -f $_.Exception.Message) -ForegroundColor Red
        }
    }
}





















