# EITAS AD Check library
# Extrait depuis Invoke-EmployeeLifecycleAgent.ps1.
# Dépendances attendues dans le worker :
# - EitasConfig.ps1
# - EitasApi.ps1
# - EitasLogging.ps1
# - EitasActiveDirectory.ps1
# Variables attendues :
# - $Config
# - $AgentName
# - $Mode

function Invoke-EitasApi {
    param(
        [string]$Method = "GET",
        [string]$Path,
        [object]$Body
    )

    return Invoke-EitasApiRequest -Method $Method -Path $Path -Body $Body -Config $Config
}
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
