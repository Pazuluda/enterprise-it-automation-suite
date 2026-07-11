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

# STEP164_AD_LOOKUP_FUNCTIONS_START

function Send-AdLookupJobResult {
    param(
        [string]$JobId,
        [bool]$Success,
        [string]$Message,
        [string]$Output,
        [object]$Result,
        [object]$Details
    )

    $Body = @{
        agent_name = $AgentName
        success = $Success
        message = $Message
        output = $Output
        result = $Result
        details = $Details
    }

    Invoke-EitasApi -Method "POST" -Path "/api/agent/ad-lookup/result/$JobId" -Body $Body | Out-Null
}

function Claim-AdLookupJob {
    param([string]$JobId)

    $Body = @{
        agent_name = $AgentName
    }

    Invoke-EitasApi -Method "POST" -Path "/api/agent/ad-lookup/claim/$JobId" -Body $Body | Out-Null
}

function Get-PendingAdLookupJobs {
    try {
        $Pending = Invoke-EitasApi -Method "GET" -Path "/api/agent/ad-lookup/pending"

        if ($null -eq $Pending) {
            return @()
        }

        if ($Pending.jobs) {
            return @($Pending.jobs)
        }

        return @()
    }
    catch {
        Write-Warning ("Impossible de recuperer les jobs recherche AD : {0}" -f $_.Exception.Message)
        return @()
    }
}

function Add-AdLookupOutputLine {
    param(
        [System.Collections.Generic.List[string]]$Lines,
        [string]$Text = ""
    )

    $Lines.Add([string]$Text) | Out-Null
    Write-Host $Text
}

function Escape-AdLookupFilterValue {
    param([string]$Value)

    if ($null -eq $Value) {
        return ""
    }

    return $Value -replace "'", "''"
}

function Invoke-EitasAdLookupJob {
    param([object]$Job)

    Import-Module ActiveDirectory -ErrorAction Stop

    $Query = [string]$Job.query
    $Query = $Query.Trim()

    if ([string]::IsNullOrWhiteSpace($Query)) {
        throw "Query recherche AD vide"
    }

    $Lines = [System.Collections.Generic.List[string]]::new()
    $Properties = @(
        "SamAccountName",
        "UserPrincipalName",
        "DisplayName",
        "Name",
        "Enabled",
        "mail",
        "Department",
        "Title",
        "Description",
        "DistinguishedName",
        "WhenCreated",
        "WhenChanged",
        "LastLogonDate",
        "Manager"
    )

    Add-AdLookupOutputLine $Lines ""
    Add-AdLookupOutputLine $Lines "============================================================"
    Add-AdLookupOutputLine $Lines "EITAS - RECHERCHE ACTIVE DIRECTORY"
    Add-AdLookupOutputLine $Lines ("Job ID : {0}" -f $Job.id)
    Add-AdLookupOutputLine $Lines ("Agent  : {0}" -f $AgentName)
    Add-AdLookupOutputLine $Lines ("Query  : {0}" -f $Query)
    Add-AdLookupOutputLine $Lines "============================================================"
    Add-AdLookupOutputLine $Lines ""

    $User = $null
    $FoundVia = ""

    try {
        $User = Get-ADUser -Identity $Query -Properties $Properties -ErrorAction Stop
        $FoundVia = "Identity"
    }
    catch {
        Add-AdLookupOutputLine $Lines "Introuvable par Identity, recherche alternative..."
    }

    if (-not $User) {
        $SafeQuery = Escape-AdLookupFilterValue $Query

        $Filter = "SamAccountName -eq '$SafeQuery' -or UserPrincipalName -eq '$SafeQuery' -or UserPrincipalName -like '$SafeQuery@*' -or mail -eq '$SafeQuery' -or DisplayName -like '*$SafeQuery*' -or Name -like '*$SafeQuery*'"

        try {
            $User = Get-ADUser -Filter $Filter -Properties $Properties | Select-Object -First 1

            if ($User) {
                $FoundVia = "Recherche alternative"
            }
        }
        catch {
            Add-AdLookupOutputLine $Lines ("Recherche alternative impossible : {0}" -f $_.Exception.Message)
        }
    }

    if (-not $User) {
        Add-AdLookupOutputLine $Lines ""
        Add-AdLookupOutputLine $Lines "UTILISATEUR AD INTROUVABLE"
        Add-AdLookupOutputLine $Lines ("Aucun objet AD trouve pour : {0}" -f $Query)

        return @{
            success = $true
            message = "Utilisateur AD introuvable"
            output = ($Lines -join [Environment]::NewLine)
            result = @{
                found = $false
                query = $Query
                groups = @()
            }
        }
    }

    Add-AdLookupOutputLine $Lines ""
    Add-AdLookupOutputLine $Lines "UTILISATEUR AD TROUVE"
    Add-AdLookupOutputLine $Lines ("Trouve via         : {0}" -f $FoundVia)
    Add-AdLookupOutputLine $Lines ("SamAccountName    : {0}" -f $User.SamAccountName)
    Add-AdLookupOutputLine $Lines ("UserPrincipalName : {0}" -f $User.UserPrincipalName)
    Add-AdLookupOutputLine $Lines ("DisplayName       : {0}" -f $User.DisplayName)
    Add-AdLookupOutputLine $Lines ("Name              : {0}" -f $User.Name)
    Add-AdLookupOutputLine $Lines ("Enabled           : {0}" -f $User.Enabled)
    Add-AdLookupOutputLine $Lines ("Mail              : {0}" -f $User.mail)
    Add-AdLookupOutputLine $Lines ("Department        : {0}" -f $User.Department)
    Add-AdLookupOutputLine $Lines ("Title             : {0}" -f $User.Title)
    Add-AdLookupOutputLine $Lines ("Description       : {0}" -f $User.Description)
    Add-AdLookupOutputLine $Lines ("DistinguishedName : {0}" -f $User.DistinguishedName)
    Add-AdLookupOutputLine $Lines ("WhenCreated       : {0}" -f $User.WhenCreated)
    Add-AdLookupOutputLine $Lines ("WhenChanged       : {0}" -f $User.WhenChanged)
    Add-AdLookupOutputLine $Lines ("LastLogonDate     : {0}" -f $User.LastLogonDate)

    $Ou = ""
    if ($User.DistinguishedName -match "^[^,]+,(.+)$") {
        $Ou = $Matches[1]
    }

    Add-AdLookupOutputLine $Lines ""
    Add-AdLookupOutputLine $Lines "GROUPES AD"

    $GroupNames = @()

    try {
        $Groups = Get-ADPrincipalGroupMembership -Identity $User.SamAccountName | Sort-Object Name
        $GroupNames = @($Groups | ForEach-Object { $_.Name })

        if ($GroupNames.Count -eq 0) {
            Add-AdLookupOutputLine $Lines "- Aucun groupe retourne"
        }
        else {
            foreach ($GroupName in $GroupNames) {
                Add-AdLookupOutputLine $Lines ("- {0}" -f $GroupName)
            }
        }
    }
    catch {
        Add-AdLookupOutputLine $Lines ("Impossible de lire les groupes : {0}" -f $_.Exception.Message)
    }

    $UserResult = @{
        found = $true
        query = $Query
        found_via = $FoundVia
        username = [string]$User.SamAccountName
        sam_account_name = [string]$User.SamAccountName
        user_principal_name = [string]$User.UserPrincipalName
        display_name = [string]$User.DisplayName
        name = [string]$User.Name
        enabled = [bool]$User.Enabled
        mail = [string]$User.mail
        department = [string]$User.Department
        title = [string]$User.Title
        description = [string]$User.Description
        distinguished_name = [string]$User.DistinguishedName
        ou = [string]$Ou
        manager = [string]$User.Manager
        when_created = [string]$User.WhenCreated
        when_changed = [string]$User.WhenChanged
        last_logon_date = [string]$User.LastLogonDate
        groups = $GroupNames
    }

    return @{
        success = $true
        message = "Utilisateur AD trouve"
        output = ($Lines -join [Environment]::NewLine)
        result = $UserResult
    }
}

function Process-PendingAdLookupJobs {
    $Jobs = Get-PendingAdLookupJobs

    if ($Jobs.Count -eq 0) {
        Write-Host "[INFO] Jobs recherche AD en attente : 0"
        return
    }

    Write-Host ("[INFO] Jobs recherche AD en attente : {0}" -f $Jobs.Count) -ForegroundColor Cyan

    foreach ($Job in $Jobs) {
        $JobId = [string]$Job.id

        Write-Host ""
        Write-Host ("=== RECHERCHE AD JOB {0} ===" -f $JobId) -ForegroundColor Cyan

        try {
            Claim-AdLookupJob -JobId $JobId
            Write-Host "[OK] Job recherche AD marque en processing." -ForegroundColor Green

            $Result = Invoke-EitasAdLookupJob -Job $Job

            Send-AdLookupJobResult -JobId $JobId -Success ([bool]$Result.success) -Message ([string]$Result.message) -Output ([string]$Result.output) -Result $Result.result -Details @{
                mode = $Mode
                agent = $AgentName
                query = $Job.query
            }

            Write-Host "[OK] Resultat recherche AD envoye a l API." -ForegroundColor Green
        }
        catch {
            $ErrorMessage = $_.Exception.Message
            Write-Host ("[ERREUR] Recherche AD : {0}" -f $ErrorMessage) -ForegroundColor Red

            try {
                Send-AdLookupJobResult -JobId $JobId -Success $false -Message $ErrorMessage -Output $ErrorMessage -Result @{
                    found = $false
                    query = $Job.query
                    groups = @()
                    error = $ErrorMessage
                } -Details @{
                    mode = $Mode
                    agent = $AgentName
                    query = $Job.query
                    error = $ErrorMessage
                }
            }
            catch {
                Write-Host ("[ERREUR] Impossible d envoyer le resultat recherche AD : {0}" -f $_.Exception.Message) -ForegroundColor Red
            }
        }
    }
}

# STEP164_AD_LOOKUP_FUNCTIONS_END


# STEP202_AD_EXPLORER_FUNCTIONS_START

function Send-AdExplorerJobResult {
    param(
        [string]$JobId,
        [bool]$Success,
        [string]$Message,
        [string]$Output,
        [object]$Result,
        [object]$Details
    )

    $Body = @{
        success = $Success
        agent_name = $AgentName
        message = $Message
        output = $Output
        result = $Result
        details = $Details
    }

    Invoke-EitasApi -Method "POST" -Path "/api/agent/ad-explorer/result/$JobId" -Body $Body | Out-Null
}

function Claim-AdExplorerJob {
    param([string]$JobId)

    $Body = @{
        agent_name = $AgentName
    }

    Invoke-EitasApi -Method "POST" -Path "/api/agent/ad-explorer/claim/$JobId" -Body $Body | Out-Null
}

function Get-PendingAdExplorerJobs {
    try {
        $Pending = Invoke-EitasApi -Method "GET" -Path "/api/agent/ad-explorer/pending"

        if ($null -eq $Pending) {
            return @()
        }

        if ($Pending.jobs) {
            return @($Pending.jobs)
        }

        return @()
    }
    catch {
        Write-Host ("[WARN] Impossible de recuperer les jobs explorateur AD : {0}" -f $_.Exception.Message) -ForegroundColor Yellow
        return @()
    }
}

function Escape-EitasLdapFilterValue {
    param([string]$Value)

    if ($null -eq $Value) {
        return ""
    }

    return $Value `
        -replace "\\", "\5c" `
        -replace "\*", "\2a" `
        -replace "\(", "\28" `
        -replace "\)", "\29" `
        -replace "`0", "\00"
}

function Convert-EitasAdUserToExplorerItem {
    param($User)

    $Groups = @()

    try {
        $Groups = @(Get-ADPrincipalGroupMembership -Identity $User.SamAccountName | Sort-Object Name | ForEach-Object {
            @{
                name = $_.Name
                sam_account_name = $_.SamAccountName
                distinguished_name = $_.DistinguishedName
            }
        })
    }
    catch {
        $Groups = @()
    }

    return @{
        type = "user"
        name = $User.Name
        display_name = $User.DisplayName
        sam_account_name = $User.SamAccountName
        user_principal_name = $User.UserPrincipalName
        email = $User.Mail
        enabled = $User.Enabled
        department = $User.Department
        title = $User.Title
        distinguished_name = $User.DistinguishedName
        groups = $Groups
        group_count = @($Groups).Count
    }
}

function Invoke-EitasAdExplorerJob {
    param($Job)

    Import-Module ActiveDirectory -ErrorAction Stop

    $Action = [string]$Job.action
    $Query = [string]$Job.query
    $BaseDn = [string]$Job.base_dn
    $Limit = 200

    if ($Job.limit) {
        try {
            $Limit = [int]$Job.limit
        }
        catch {
            $Limit = 200
        }
    }

    if ($Limit -lt 1) { $Limit = 1 }
    if ($Limit -gt 1000) { $Limit = 1000 }

    $IncludeDisabled = $true
    if ($null -ne $Job.include_disabled) {
        $IncludeDisabled = [bool]$Job.include_disabled
    }

    $Items = @()
    $Lines = @()

    if ($Action -eq "list_ous") {
        $Params = @{
            Filter = "*"
            Properties = @("CanonicalName", "Description", "ProtectedFromAccidentalDeletion")
            ResultSetSize = $Limit
        }

        if (-not [string]::IsNullOrWhiteSpace($BaseDn)) {
            $Params.SearchBase = $BaseDn
        }

        $Ous = @(Get-ADOrganizationalUnit @Params | Sort-Object DistinguishedName)

        $Items = @($Ous | ForEach-Object {
            @{
                type = "ou"
                name = $_.Name
                canonical_name = $_.CanonicalName
                description = $_.Description
                protected = $_.ProtectedFromAccidentalDeletion
                distinguished_name = $_.DistinguishedName
            }
        })

        $Lines += "OU trouvees : $(@($Items).Count)"
    }
    elseif ($Action -eq "list_groups") {
        $Params = @{
            Filter = "*"
            Properties = @("Description", "GroupScope", "GroupCategory", "SamAccountName")
            ResultSetSize = $Limit
        }

        if (-not [string]::IsNullOrWhiteSpace($BaseDn)) {
            $Params.SearchBase = $BaseDn
        }

        $Groups = @(Get-ADGroup @Params | Sort-Object Name)

        $Items = @($Groups | ForEach-Object {
            @{
                type = "group"
                name = $_.Name
                sam_account_name = $_.SamAccountName
                scope = [string]$_.GroupScope
                category = [string]$_.GroupCategory
                description = $_.Description
                distinguished_name = $_.DistinguishedName
            }
        })

        $Lines += "Groupes trouves : $(@($Items).Count)"
    }
    elseif ($Action -eq "search_users") {
        if ([string]::IsNullOrWhiteSpace($Query)) {
            $LdapFilter = "(&(objectCategory=person)(objectClass=user))"
        }
        else {
            $Escaped = Escape-EitasLdapFilterValue -Value $Query
            $LdapFilter = "(|(cn=*$Escaped*)(sAMAccountName=*$Escaped*)(displayName=*$Escaped*)(mail=*$Escaped*)(userPrincipalName=*$Escaped*))"
        }

        $Params = @{
            LDAPFilter = $LdapFilter
            Properties = @("DisplayName", "Mail", "Department", "Title", "Enabled", "UserPrincipalName")
            ResultSetSize = $Limit
        }

        if (-not [string]::IsNullOrWhiteSpace($BaseDn)) {
            $Params.SearchBase = $BaseDn
        }

        $Users = @(Get-ADUser @Params | Sort-Object SamAccountName)

        if (-not $IncludeDisabled) {
            $Users = @($Users | Where-Object { $_.Enabled -eq $true })
        }

        $Items = @($Users | ForEach-Object {
            Convert-EitasAdUserToExplorerItem -User $_
        })

        $Lines += "Utilisateurs trouves : $(@($Items).Count)"
    }
    elseif ($Action -eq "get_user") {
        $Escaped = Escape-EitasLdapFilterValue -Value $Query
        $LdapFilter = "(|(sAMAccountName=$Escaped)(userPrincipalName=$Escaped)(mail=$Escaped)(cn=$Escaped))"

        $Params = @{
            LDAPFilter = $LdapFilter
            Properties = @("DisplayName", "Mail", "Department", "Title", "Enabled", "UserPrincipalName")
            ResultSetSize = 1
        }

        if (-not [string]::IsNullOrWhiteSpace($BaseDn)) {
            $Params.SearchBase = $BaseDn
        }

        $User = @(Get-ADUser @Params | Select-Object -First 1)

        if ($User.Count -eq 0) {
            return @{
                success = $true
                message = "Utilisateur AD introuvable"
                output = "Utilisateur AD introuvable : $Query"
                result = @{
                    action = $Action
                    query = $Query
                    found = $false
                    count = 0
                    items = @()
                }
            }
        }

        $Item = Convert-EitasAdUserToExplorerItem -User $User[0]
        $Items = @($Item)

        $Lines += "Utilisateur trouve : $($Item.sam_account_name)"
        $Lines += "Nom : $($Item.display_name)"
        $Lines += "OU/DN : $($Item.distinguished_name)"
        $Lines += "Groupes : $($Item.group_count)"
    }
    elseif ($Action -eq "get_group_members") {
        $Group = Get-ADGroup -Identity $Query -Properties Description, GroupScope, GroupCategory, SamAccountName -ErrorAction Stop
        $Recursive = [bool]$Job.recursive

        $Members = @(Get-ADGroupMember -Identity $Group.DistinguishedName -Recursive:$Recursive | Select-Object -First $Limit)

        $Items = @($Members | ForEach-Object {
            $Member = $_

            if ($Member.objectClass -eq "user") {
                try {
                    $FullUser = Get-ADUser -Identity $Member.DistinguishedName -Properties DisplayName, Mail, Department, Title, Enabled, UserPrincipalName
                    Convert-EitasAdUserToExplorerItem -User $FullUser
                }
                catch {
                    @{
                        type = "user"
                        name = $Member.Name
                        sam_account_name = $Member.SamAccountName
                        distinguished_name = $Member.DistinguishedName
                    }
                }
            }
            else {
                @{
                    type = $Member.objectClass
                    name = $Member.Name
                    sam_account_name = $Member.SamAccountName
                    distinguished_name = $Member.DistinguishedName
                }
            }
        })

        $Lines += "Groupe : $($Group.Name)"
        $Lines += "Membres trouves : $(@($Items).Count)"
    }
    else {
        throw "Action AD Explorer non supportee par l agent : $Action"
    }

    return @{
        success = $true
        message = "Exploration AD terminee"
        output = ($Lines -join [Environment]::NewLine)
        result = @{
            action = $Action
            query = $Query
            base_dn = $BaseDn
            count = @($Items).Count
            items = $Items
        }
    }
}

function Process-PendingAdExplorerJobs {
    $Jobs = Get-PendingAdExplorerJobs

    if ($Jobs.Count -eq 0) {
        Write-Host "[INFO] Aucun job explorateur AD en attente."
        return
    }

    Write-Host ("[INFO] Jobs explorateur AD en attente : {0}" -f $Jobs.Count) -ForegroundColor Cyan

    foreach ($Job in $Jobs) {
        $JobId = [string]$Job.id

        if ([string]::IsNullOrWhiteSpace($JobId)) {
            continue
        }

        Write-Host ("[INFO] Traitement exploration AD {0} action={1} query={2}" -f $JobId, $Job.action, $Job.query) -ForegroundColor Cyan

        try {
            Claim-AdExplorerJob -JobId $JobId
            Write-Host "[OK] Job explorateur AD marque en processing." -ForegroundColor Green

            $Result = Invoke-EitasAdExplorerJob -Job $Job

            Send-AdExplorerJobResult `
                -JobId $JobId `
                -Success ([bool]$Result.success) `
                -Message ([string]$Result.message) `
                -Output ([string]$Result.output) `
                -Result $Result.result `
                -Details @{
                    mode = $Mode
                    agent = $AgentName
                    read_only = $true
                }

            Write-Host "[OK] Resultat explorateur AD envoye a l API." -ForegroundColor Green
        }
        catch {
            $ErrorMessage = $_.Exception.Message
            Write-Host ("[ERREUR] Exploration AD : {0}" -f $ErrorMessage) -ForegroundColor Red

            try {
                Send-AdExplorerJobResult `
                    -JobId $JobId `
                    -Success $false `
                    -Message $ErrorMessage `
                    -Output $ErrorMessage `
                    -Result @{
                        action = $Job.action
                        query = $Job.query
                        count = 0
                        items = @()
                    } `
                    -Details @{
                        mode = $Mode
                        agent = $AgentName
                        read_only = $true
                        error = $ErrorMessage
                    }
            }
            catch {
                Write-Host ("[ERREUR] Impossible d envoyer le resultat explorateur AD : {0}" -f $_.Exception.Message) -ForegroundColor Red
            }
        }
    }
}

# STEP202_AD_EXPLORER_FUNCTIONS_END


# STEP208_AD_ADMIN_FUNCTIONS_START

function Send-AdAdminJobResult {
    param(
        [string]$JobId,
        [bool]$Success,
        [string]$Message,
        [string]$Output,
        [object]$Result,
        [object]$Details
    )

    $Body = @{
        success = $Success
        agent_name = $AgentName
        message = $Message
        output = $Output
        result = $Result
        details = $Details
    }

    Invoke-EitasApi -Method "POST" -Path "/api/agent/ad-admin/result/$JobId" -Body $Body | Out-Null
}

function Claim-AdAdminJob {
    param([string]$JobId)

    $Body = @{
        agent_name = $AgentName
    }

    Invoke-EitasApi -Method "POST" -Path "/api/agent/ad-admin/claim/$JobId" -Body $Body | Out-Null
}

function Get-PendingAdAdminJobs {
    try {
        $Pending = Invoke-EitasApi -Method "GET" -Path "/api/agent/ad-admin/pending"

        if ($null -eq $Pending) {
            return @()
        }

        if ($Pending.jobs) {
            return @($Pending.jobs)
        }

        return @()
    }
    catch {
        Write-Host ("[WARN] Impossible de recuperer les jobs AD Admin : {0}" -f $_.Exception.Message) -ForegroundColor Yellow
        return @()
    }
}

function Test-EitasAdObjectExists {
    param(
        [string]$LdapFilter,
        [string]$SearchBase
    )

    try {
        $Params = @{
            LDAPFilter = $LdapFilter
            ErrorAction = "Stop"
        }

        if (-not [string]::IsNullOrWhiteSpace($SearchBase)) {
            $Params.SearchBase = $SearchBase
        }

        $Found = @(Get-ADObject @Params | Select-Object -First 1)
        return ($Found.Count -gt 0)
    }
    catch {
        return $false
    }
}

function Invoke-EitasAdAdminJob {
    param($Job)

    Import-Module ActiveDirectory -ErrorAction Stop

    $Action = [string]$Job.action
    $Payload = $Job.payload

    if ($null -eq $Payload) {
        throw "Payload AD Admin manquant"
    }

    $ParentDn = [string]$Payload.parent_dn
    $Name = [string]$Payload.name
    $Description = [string]$Payload.description

    if ([string]::IsNullOrWhiteSpace($ParentDn)) {
        throw "parent_dn manquant"
    }

    if ([string]::IsNullOrWhiteSpace($Name)) {
        throw "name manquant"
    }

    if ($Mode -ne "Production") {
        $SimulatedDn = if ($Action -eq "create_ou") {
            "OU=$Name,$ParentDn"
        }
        else {
            "CN=$Name,$ParentDn"
        }

        return @{
            success = $true
            message = "Simulation AD Admin terminee"
            output = "Mode Simulation : aucune modification AD executee.`nAction : $Action`nNom : $Name`nParent : $ParentDn"
            result = @{
                action = $Action
                created = $false
                simulated = $true
                name = $Name
                parent_dn = $ParentDn
                distinguished_name = $SimulatedDn
            }
        }
    }

    if ($Action -eq "create_ou") {
        $EscapedName = Escape-EitasLdapFilterValue -Value $Name
        $Exists = Test-EitasAdObjectExists -SearchBase $ParentDn -LdapFilter "(&(objectClass=organizationalUnit)(ou=$EscapedName))"

        if ($Exists) {
            throw "Une OU existe deja avec ce nom dans ce parent : $Name"
        }

        $Params = @{
            Name = $Name
            Path = $ParentDn
            ProtectedFromAccidentalDeletion = $true
            ErrorAction = "Stop"
        }

        if (-not [string]::IsNullOrWhiteSpace($Description)) {
            $Params.Description = $Description
        }

        New-ADOrganizationalUnit @Params

        $Created = Get-ADOrganizationalUnit `
            -LDAPFilter "(&(objectClass=organizationalUnit)(ou=$EscapedName))" `
            -SearchBase $ParentDn `
            -Properties CanonicalName, Description, ProtectedFromAccidentalDeletion `
            -ErrorAction Stop |
            Select-Object -First 1

        return @{
            success = $true
            message = "OU creee dans Active Directory"
            output = "OU creee : $Name`nParent : $ParentDn`nDN : $($Created.DistinguishedName)"
            result = @{
                action = $Action
                created = $true
                name = $Created.Name
                description = $Created.Description
                canonical_name = $Created.CanonicalName
                distinguished_name = $Created.DistinguishedName
                protected = $Created.ProtectedFromAccidentalDeletion
            }
        }
    }

    if ($Action -eq "create_group") {
        $SamAccountName = [string]$Payload.sam_account_name
        $GroupScope = [string]$Payload.group_scope
        $GroupCategory = [string]$Payload.group_category

        if ([string]::IsNullOrWhiteSpace($SamAccountName)) {
            $SamAccountName = $Name
        }

        if ([string]::IsNullOrWhiteSpace($GroupScope)) {
            $GroupScope = "Global"
        }

        if ([string]::IsNullOrWhiteSpace($GroupCategory)) {
            $GroupCategory = "Security"
        }

        $EscapedSam = Escape-EitasLdapFilterValue -Value $SamAccountName
        $Exists = Test-EitasAdObjectExists -LdapFilter "(&(objectClass=group)(sAMAccountName=$EscapedSam))" -SearchBase ""

        if ($Exists) {
            throw "Un groupe existe deja avec ce SamAccountName : $SamAccountName"
        }

        $Params = @{
            Name = $Name
            SamAccountName = $SamAccountName
            GroupScope = $GroupScope
            GroupCategory = $GroupCategory
            Path = $ParentDn
            ErrorAction = "Stop"
        }

        if (-not [string]::IsNullOrWhiteSpace($Description)) {
            $Params.Description = $Description
        }

        New-ADGroup @Params

        $Created = Get-ADGroup `
            -Identity $SamAccountName `
            -Properties Description, GroupScope, GroupCategory, SamAccountName `
            -ErrorAction Stop

        return @{
            success = $true
            message = "Groupe cree dans Active Directory"
            output = "Groupe cree : $Name`nSamAccountName : $SamAccountName`nParent : $ParentDn`nDN : $($Created.DistinguishedName)"
            result = @{
                action = $Action
                created = $true
                name = $Created.Name
                sam_account_name = $Created.SamAccountName
                description = $Created.Description
                group_scope = [string]$Created.GroupScope
                group_category = [string]$Created.GroupCategory
                distinguished_name = $Created.DistinguishedName
            }
        }
    }

    throw "Action AD Admin non supportee par l agent : $Action"
}

function Process-PendingAdAdminJobs {
    $Jobs = Get-PendingAdAdminJobs

    if ($Jobs.Count -eq 0) {
        Write-Host "[INFO] Aucun job AD Admin en attente."
        return
    }

    Write-Host ("[INFO] Jobs AD Admin en attente : {0}" -f $Jobs.Count) -ForegroundColor Cyan

    foreach ($Job in $Jobs) {
        $JobId = [string]$Job.id

        if ([string]::IsNullOrWhiteSpace($JobId)) {
            continue
        }

        Write-Host ("[INFO] Traitement AD Admin {0} action={1}" -f $JobId, $Job.action) -ForegroundColor Cyan

        try {
            Claim-AdAdminJob -JobId $JobId
            Write-Host "[OK] Job AD Admin marque en processing." -ForegroundColor Green

            $Result = Invoke-EitasAdAdminJob -Job $Job

            Send-AdAdminJobResult `
                -JobId $JobId `
                -Success ([bool]$Result.success) `
                -Message ([string]$Result.message) `
                -Output ([string]$Result.output) `
                -Result $Result.result `
                -Details @{
                    mode = $Mode
                    agent = $AgentName
                    write_operation = $true
                }

            Write-Host "[OK] Resultat AD Admin envoye a l API." -ForegroundColor Green
        }
        catch {
            $ErrorMessage = $_.Exception.Message
            Write-Host ("[ERREUR] AD Admin : {0}" -f $ErrorMessage) -ForegroundColor Red

            try {
                Send-AdAdminJobResult `
                    -JobId $JobId `
                    -Success $false `
                    -Message $ErrorMessage `
                    -Output $ErrorMessage `
                    -Result @{
                        action = $Job.action
                        created = $false
                        error = $ErrorMessage
                    } `
                    -Details @{
                        mode = $Mode
                        agent = $AgentName
                        write_operation = $true
                        error = $ErrorMessage
                    }
            }
            catch {
                Write-Host ("[ERREUR] Impossible d envoyer le resultat AD Admin : {0}" -f $_.Exception.Message) -ForegroundColor Red
            }
        }
    }
}

# STEP208_AD_ADMIN_FUNCTIONS_END

# STEP162_AD_CHECK_FUNCTIONS_START

function Send-AdCheckJobResult {
    param(
        [string]$JobId,
        [bool]$Success,
        [string]$Message,
        [string]$Output,
        [object]$Summary,
        [object]$Details
    )

    $Body = @{
        agent_name = $AgentName
        success = $Success
        message = $Message
        output = $Output
        summary = $Summary
        details = $Details
    }

    Invoke-EitasApi -Method "POST" -Path "/api/agent/ad-check/result/$JobId" -Body $Body | Out-Null
}

function Claim-AdCheckJob {
    param([string]$JobId)

    $Body = @{
        agent_name = $AgentName
    }

    Invoke-EitasApi -Method "POST" -Path "/api/agent/ad-check/claim/$JobId" -Body $Body | Out-Null
}

function Get-PendingAdCheckJobs {
    try {
        $Pending = Invoke-EitasApi -Method "GET" -Path "/api/agent/ad-check/pending"

        if ($null -eq $Pending) {
            return @()
        }

        if ($Pending.jobs) {
            return @($Pending.jobs)
        }

        return @()
    }
    catch {
        Write-Warning ("Impossible de recuperer les jobs controle AD : {0}" -f $_.Exception.Message)
        return @()
    }
}

function Add-AdCheckOutputLine {
    param(
        [System.Collections.Generic.List[string]]$Lines,
        [string]$Text = ""
    )

    $Lines.Add([string]$Text) | Out-Null
    Write-Host $Text
}

function Get-EitasObjectValue {
    param(
        [object]$Object,
        [string[]]$Names
    )

    if ($null -eq $Object) {
        return ""
    }

    foreach ($Name in $Names) {
        $Property = $Object.PSObject.Properties[$Name]

        if ($null -ne $Property -and $null -ne $Property.Value) {
            $Value = [string]$Property.Value

            if (-not [string]::IsNullOrWhiteSpace($Value)) {
                return $Value
            }
        }
    }

    return ""
}

function Escape-AdFilterValue {
    param([string]$Value)

    if ($null -eq $Value) {
        return ""
    }

    return $Value -replace "'", "''"
}

function Test-EitasAdCheckSimulation {
    param([object]$Request)

    $Values = @()

    if ($Request.mode) {
        $Values += [string]$Request.mode
    }

    if ($Request.ad_payload -and $Request.ad_payload.mode) {
        $Values += [string]$Request.ad_payload.mode
    }

    if ($Request.agent_result -and $Request.agent_result.details) {
        $Details = $Request.agent_result.details

        if ($Details.simulated -eq $true -or $Details.simulation -eq $true) {
            return $true
        }

        if ($Details.mode) {
            $Values += [string]$Details.mode
        }
    }

    return (($Values -join " ").ToLowerInvariant().Contains("simulation"))
}

function Invoke-EitasAdCheckJob {
    param([object]$Job)

    Import-Module ActiveDirectory -ErrorAction Stop

    $Lines = [System.Collections.Generic.List[string]]::new()
    $Requests = @($Job.requests)

    $FoundCount = 0
    $MissingCount = 0
    $OkOuCount = 0
    $WarningCount = 0
    $Index = 0

    $Properties = @(
        "SamAccountName",
        "DisplayName",
        "Enabled",
        "mail",
        "Department",
        "Title",
        "Description",
        "DistinguishedName",
        "WhenCreated",
        "WhenChanged",
        "LastLogonDate"
    )

    Add-AdCheckOutputLine $Lines ""
    Add-AdCheckOutputLine $Lines "============================================================"
    Add-AdCheckOutputLine $Lines "EITAS - CONTROLE AD EN MASSE"
    Add-AdCheckOutputLine $Lines ("Job ID              : {0}" -f $Job.id)
    Add-AdCheckOutputLine $Lines ("Agent               : {0}" -f $AgentName)
    Add-AdCheckOutputLine $Lines ("Demandes a controler: {0}" -f $Requests.Count)
    Add-AdCheckOutputLine $Lines "============================================================"

    foreach ($Request in $Requests) {
        $Index += 1
        $Payload = $Request.ad_payload

        if ($null -eq $Payload) {
            $Payload = $Request.payload
        }

        $Type = Get-RequestType -Request $Request
        $Username = Get-EitasObjectValue -Object $Payload -Names @("username", "login", "sam_account_name", "samAccountName", "sam")
        $DisplayName = Get-EitasObjectValue -Object $Payload -Names @("display_name", "full_name", "name")
        $ExpectedOu = Get-EitasObjectValue -Object $Payload -Names @("ou", "target_ou", "ou_path", "organizational_unit", "move_to_ou")
        $Simulated = Test-EitasAdCheckSimulation -Request $Request

        $User = $null
        $FoundVia = ""

        Add-AdCheckOutputLine $Lines ""
        Add-AdCheckOutputLine $Lines "------------------------------------------------------------"
        Add-AdCheckOutputLine $Lines ("DEMANDE {0}/{1}" -f $Index, $Requests.Count)
        Add-AdCheckOutputLine $Lines "------------------------------------------------------------"
        Add-AdCheckOutputLine $Lines ("ID demande        : {0}" -f $Request.id)
        Add-AdCheckOutputLine $Lines ("Type              : {0}" -f $Type)
        Add-AdCheckOutputLine $Lines ("Statut portail    : {0}" -f $Request.status)
        Add-AdCheckOutputLine $Lines ("SamAccountName    : {0}" -f $Username)
        Add-AdCheckOutputLine $Lines ("Nom attendu       : {0}" -f $DisplayName)
        Add-AdCheckOutputLine $Lines ("OU attendue       : {0}" -f $ExpectedOu)
        Add-AdCheckOutputLine $Lines ("Simulation        : {0}" -f $Simulated)

        if ([string]::IsNullOrWhiteSpace($Username) -and [string]::IsNullOrWhiteSpace($DisplayName)) {
            Add-AdCheckOutputLine $Lines "DONNEES INSUFFISANTES : aucun login ni nom pour rechercher l'utilisateur."
            $MissingCount += 1
            continue
        }

        if (-not [string]::IsNullOrWhiteSpace($Username)) {
            try {
                $User = Get-ADUser -Identity $Username -Properties $Properties -ErrorAction Stop
                $FoundVia = "Identity"
            }
            catch {
                Add-AdCheckOutputLine $Lines "Introuvable par Identity, recherche alternative..."
            }
        }

        if (-not $User) {
            $Conditions = @()

            if (-not [string]::IsNullOrWhiteSpace($Username)) {
                $FilterSam = Escape-AdFilterValue $Username
                $Conditions += "SamAccountName -eq '$FilterSam'"
                $Conditions += "UserPrincipalName -like '$FilterSam@*'"
            }

            if (-not [string]::IsNullOrWhiteSpace($DisplayName)) {
                $FilterName = Escape-AdFilterValue $DisplayName
                $Conditions += "DisplayName -eq '$FilterName'"
                $Conditions += "Name -eq '$FilterName'"
            }

            if ($Conditions.Count -gt 0) {
                $Filter = $Conditions -join " -or "

                try {
                    $User = Get-ADUser -Filter $Filter -Properties $Properties | Select-Object -First 1

                    if ($User) {
                        $FoundVia = "Recherche alternative"
                    }
                }
                catch {
                    Add-AdCheckOutputLine $Lines ("Recherche alternative impossible : {0}" -f $_.Exception.Message)
                }
            }
        }

        if (-not $User) {
            Add-AdCheckOutputLine $Lines ""
            Add-AdCheckOutputLine $Lines "UTILISATEUR AD INTROUVABLE"
            Add-AdCheckOutputLine $Lines ("Aucun objet AD trouve pour : {0} / {1}" -f $Username, $DisplayName)

            if ($Simulated) {
                Add-AdCheckOutputLine $Lines "INFO : cette demande etait en Simulation."
                Add-AdCheckOutputLine $Lines "Donc aucun changement AD reel nest attendu pour cette demande."
            }
            else {
                Add-AdCheckOutputLine $Lines "Attention : demande non detectee comme Simulation. Verifier si compte supprime, renomme ou historique."
                $WarningCount += 1
            }

            $MissingCount += 1
            continue
        }

        $FoundCount += 1

        Add-AdCheckOutputLine $Lines ""
        Add-AdCheckOutputLine $Lines "UTILISATEUR AD TROUVE"
        Add-AdCheckOutputLine $Lines ("Trouve via : {0}" -f $FoundVia)
        Add-AdCheckOutputLine $Lines ("SamAccountName    : {0}" -f $User.SamAccountName)
        Add-AdCheckOutputLine $Lines ("DisplayName       : {0}" -f $User.DisplayName)
        Add-AdCheckOutputLine $Lines ("Enabled           : {0}" -f $User.Enabled)
        Add-AdCheckOutputLine $Lines ("Mail              : {0}" -f $User.mail)
        Add-AdCheckOutputLine $Lines ("Department        : {0}" -f $User.Department)
        Add-AdCheckOutputLine $Lines ("Title             : {0}" -f $User.Title)
        Add-AdCheckOutputLine $Lines ("Description       : {0}" -f $User.Description)
        Add-AdCheckOutputLine $Lines ("DistinguishedName : {0}" -f $User.DistinguishedName)
        Add-AdCheckOutputLine $Lines ("WhenCreated       : {0}" -f $User.WhenCreated)
        Add-AdCheckOutputLine $Lines ("WhenChanged       : {0}" -f $User.WhenChanged)
        Add-AdCheckOutputLine $Lines ("LastLogonDate     : {0}" -f $User.LastLogonDate)

        Add-AdCheckOutputLine $Lines ""
        Add-AdCheckOutputLine $Lines "GROUPES AD"

        try {
            $Groups = Get-ADPrincipalGroupMembership -Identity $User.SamAccountName | Sort-Object Name

            foreach ($Group in $Groups) {
                Add-AdCheckOutputLine $Lines ("- {0}" -f $Group.Name)
            }
        }
        catch {
            Add-AdCheckOutputLine $Lines ("Impossible de lire les groupes : {0}" -f $_.Exception.Message)
            $WarningCount += 1
        }

        Add-AdCheckOutputLine $Lines ""
        Add-AdCheckOutputLine $Lines "CONTROLE OU"

        if (-not [string]::IsNullOrWhiteSpace($ExpectedOu)) {
            Add-AdCheckOutputLine $Lines ("OU attendue : {0}" -f $ExpectedOu)
            Add-AdCheckOutputLine $Lines ("DN actuel   : {0}" -f $User.DistinguishedName)

            if ($User.DistinguishedName -like "*,$ExpectedOu") {
                Add-AdCheckOutputLine $Lines "OK : utilisateur dans OU attendue"
                $OkOuCount += 1
            }
            else {
                Add-AdCheckOutputLine $Lines "WARNING : utilisateur hors OU attendue"
                $WarningCount += 1
            }
        }
        else {
            Add-AdCheckOutputLine $Lines "Aucune OU attendue dans la demande."
        }

        Add-AdCheckOutputLine $Lines ""
        Add-AdCheckOutputLine $Lines "CONTROLE ETAT COMPTE"
        Add-AdCheckOutputLine $Lines ("Enabled actuel : {0}" -f $User.Enabled)

        if ($Type -eq "offboarding") {
            if (-not $User.Enabled) {
                Add-AdCheckOutputLine $Lines "OK : compte desactive pour offboarding"
            }
            else {
                Add-AdCheckOutputLine $Lines "WARNING : compte encore actif pour offboarding"
                $WarningCount += 1
            }
        }
        elseif ($Type -eq "onboarding" -or $Type -eq "modification") {
            if ($User.Enabled) {
                Add-AdCheckOutputLine $Lines "OK : compte actif"
            }
            else {
                Add-AdCheckOutputLine $Lines "WARNING : compte desactive"
                $WarningCount += 1
            }
        }
    }

    Add-AdCheckOutputLine $Lines ""
    Add-AdCheckOutputLine $Lines "============================================================"
    Add-AdCheckOutputLine $Lines "RESUME CONTROLE AD EN MASSE"
    Add-AdCheckOutputLine $Lines ("Demandes controlees       : {0}" -f $Requests.Count)
    Add-AdCheckOutputLine $Lines ("Utilisateurs trouves      : {0}" -f $FoundCount)
    Add-AdCheckOutputLine $Lines ("Utilisateurs introuvables : {0}" -f $MissingCount)
    Add-AdCheckOutputLine $Lines ("OU OK                     : {0}" -f $OkOuCount)
    Add-AdCheckOutputLine $Lines ("Warnings                  : {0}" -f $WarningCount)
    Add-AdCheckOutputLine $Lines "============================================================"

    return @{
        output = ($Lines -join [Environment]::NewLine)
        summary = @{
            checked = $Requests.Count
            found = $FoundCount
            missing = $MissingCount
            ou_ok = $OkOuCount
            warnings = $WarningCount
        }
    }
}

function Process-PendingAdCheckJobs {
    $Jobs = Get-PendingAdCheckJobs

    if ($Jobs.Count -eq 0) {
        Write-Host "[INFO] Jobs controle AD en attente : 0"
        return
    }

    Write-Host ("[INFO] Jobs controle AD en attente : {0}" -f $Jobs.Count) -ForegroundColor Cyan

    foreach ($Job in $Jobs) {
        $JobId = [string]$Job.id

        Write-Host ""
        Write-Host ("=== CONTROLE AD JOB {0} ===" -f $JobId) -ForegroundColor Cyan

        try {
            Claim-AdCheckJob -JobId $JobId
            Write-Host "[OK] Job controle AD marque en processing." -ForegroundColor Green

            $Result = Invoke-EitasAdCheckJob -Job $Job

            Send-AdCheckJobResult -JobId $JobId -Success $true -Message "Controle AD termine" -Output ([string]$Result.output) -Summary $Result.summary -Details @{
                mode = $Mode
                agent = $AgentName
            }

            Write-Host "[OK] Resultat controle AD envoye a l API." -ForegroundColor Green
        }
        catch {
            $ErrorMessage = $_.Exception.Message
            Write-Host ("[ERREUR] Controle AD : {0}" -f $ErrorMessage) -ForegroundColor Red

            try {
                Send-AdCheckJobResult -JobId $JobId -Success $false -Message $ErrorMessage -Output $ErrorMessage -Summary @{
                    checked = 0
                    found = 0
                    missing = 0
                    ou_ok = 0
                    warnings = 1
                } -Details @{
                    mode = $Mode
                    agent = $AgentName
                    error = $ErrorMessage
                }
            }
            catch {
                Write-Host ("[ERREUR] Impossible d envoyer le resultat controle AD : {0}" -f $_.Exception.Message) -ForegroundColor Red
            }
        }
    }
}

# STEP162_AD_CHECK_FUNCTIONS_END

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




















