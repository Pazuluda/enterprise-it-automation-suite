function Get-EitasObjectValue {
    param(
        [object]$Object,
        [string[]]$Names
    )

    if ($null -eq $Object) {
        return $null
    }

    foreach ($Name in $Names) {
        if ($Object.PSObject.Properties.Name -contains $Name) {
            $Value = $Object.$Name
            if ($null -ne $Value -and "$Value" -ne "") {
                return $Value
            }
        }
    }

    return $null
}

function Get-EitasResponseItems {
    param([object]$Response)

    if ($null -eq $Response) {
        return @()
    }

    if ($Response -is [array]) {
        return @($Response)
    }

    foreach ($Name in @("jobs", "items", "data", "results", "pending")) {
        if ($Response.PSObject.Properties.Name -contains $Name -and $null -ne $Response.$Name) {
            return @($Response.$Name)
        }
    }

    return @($Response)
}

function Get-EitasAdAdminJobPayload {
    param([object]$Job)

    $Payload = Get-EitasObjectValue -Object $Job -Names @("payload", "data", "parameters", "params")

    if ($null -eq $Payload) {
        return $Job
    }

    return $Payload
}

function Get-EitasAdAdminJobId {
    param([object]$Job)

    return Get-EitasObjectValue -Object $Job -Names @("id", "job_id", "jobId", "request_id")
}

function Get-EitasAdAdminJobAction {
    param([object]$Job)

    $Payload = Get-EitasAdAdminJobPayload -Job $Job

    $Action = Get-EitasObjectValue -Object $Job -Names @("action", "type", "job_type")
    if ($Action) { return [string]$Action }

    return [string](Get-EitasObjectValue -Object $Payload -Names @("action", "type", "job_type"))
}

function Get-EitasPendingAdAdminJobs {
    param([object]$Config)

    $Response = Invoke-EitasApiRequest -Method "GET" -Path "/api/agent/ad-admin/pending" -Config $Config
    return @(Get-EitasResponseItems -Response $Response)
}

function Claim-EitasAdAdminJob {
    param(
        [object]$Config,
        [string]$JobId,
        [string]$AgentName
    )

    try {
        return Invoke-EitasApiRequest `
            -Method "POST" `
            -Path "/api/agent/ad-admin/claim/$JobId" `
            -Body @{
                agent_name = $AgentName
                processing_by = $AgentName
            } `
            -Config $Config
    }
    catch {
        $Message = $_.Exception.Message

        if ($Message -match "409|Conflict|non disponible|Statut actuel|déjà|deja") {
            Write-EitasLog -Name "ad-admin-worker-light.log" -Level "WARN" -Message "Job AD Admin déjà pris, ignoré : $JobId" -Console
            return $null
        }

        throw
    }
}

function Send-EitasAdAdminJobResult {
    param(
        [object]$Config,
        [string]$JobId,
        [bool]$Success,
        [string]$Message,
        [object]$Output,
        [string]$AgentName
    )

    return Invoke-EitasApiRequest `
        -Method "POST" `
        -Path "/api/agent/ad-admin/result/$JobId" `
        -Body @{
            success = $Success
            message = $Message
            output = $Output
            agent_name = $AgentName
            completed_by = $AgentName
        } `
        -Config $Config
}

function Invoke-EitasAdAdminCreateOu {
    param(
        [object]$Config,
        [object]$Payload,
        [string]$Mode
    )

    $Name = Get-EitasObjectValue -Object $Payload -Names @("name", "ou_name", "ouName", "display_name")
    $ParentDn = Get-EitasObjectValue -Object $Payload -Names @("parent_dn", "parentDn", "target_dn", "targetDn", "path")
    $Description = Get-EitasObjectValue -Object $Payload -Names @("description", "comment")

    if ([string]::IsNullOrWhiteSpace($Name)) {
        throw "Nom OU manquant"
    }

    if ([string]::IsNullOrWhiteSpace($ParentDn)) {
        throw "Parent DN manquant pour création OU"
    }

    Assert-EitasDnSafe -DistinguishedName $ParentDn -Config $Config | Out-Null

    if ($Mode -ne "Production") {
        return [pscustomobject]@{
            action = "create_ou"
            simulated = $true
            name = $Name
            parent_dn = $ParentDn
            message = "Simulation création OU"
        }
    }

    Import-EitasActiveDirectoryModule | Out-Null

    if (Test-EitasAdObjectExists -Identity $Name -SearchBase $ParentDn -ObjectClass "organizationalUnit") {
        throw "OU déjà existante : $Name dans $ParentDn"
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

    return [pscustomobject]@{
        action = "create_ou"
        simulated = $false
        name = $Name
        parent_dn = $ParentDn
        distinguished_name = "OU=$Name,$ParentDn"
        message = "OU créée"
    }
}

function Invoke-EitasAdAdminCreateGroup {
    param(
        [object]$Config,
        [object]$Payload,
        [string]$Mode
    )

    $Name = Get-EitasObjectValue -Object $Payload -Names @("name", "group_name", "groupName", "display_name")
    $SamAccountName = Get-EitasObjectValue -Object $Payload -Names @("sam_account_name", "samAccountName", "sAMAccountName")
    $ParentDn = Get-EitasObjectValue -Object $Payload -Names @("parent_dn", "parentDn", "target_dn", "targetDn", "path")
    $Description = Get-EitasObjectValue -Object $Payload -Names @("description", "comment")
    $GroupScope = Get-EitasObjectValue -Object $Payload -Names @("group_scope", "groupScope", "scope")
    $GroupCategory = Get-EitasObjectValue -Object $Payload -Names @("group_category", "groupCategory", "category")

    if ([string]::IsNullOrWhiteSpace($Name)) {
        throw "Nom groupe manquant"
    }

    if ([string]::IsNullOrWhiteSpace($SamAccountName)) {
        $SamAccountName = $Name
    }

    if ([string]::IsNullOrWhiteSpace($ParentDn)) {
        throw "Parent DN manquant pour création groupe"
    }

    if ([string]::IsNullOrWhiteSpace($GroupScope)) {
        $GroupScope = "Global"
    }

    if ([string]::IsNullOrWhiteSpace($GroupCategory)) {
        $GroupCategory = "Security"
    }

    Assert-EitasDnSafe -DistinguishedName $ParentDn -Config $Config | Out-Null

    if ($Mode -ne "Production") {
        return [pscustomobject]@{
            action = "create_group"
            simulated = $true
            name = $Name
            sam_account_name = $SamAccountName
            parent_dn = $ParentDn
            group_scope = $GroupScope
            group_category = $GroupCategory
            message = "Simulation création groupe"
        }
    }

    Import-EitasActiveDirectoryModule | Out-Null

    if (Test-EitasAdObjectExists -Identity $SamAccountName -SearchBase $ParentDn -ObjectClass "group") {
        throw "Groupe déjà existant : $SamAccountName dans $ParentDn"
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

    return [pscustomobject]@{
        action = "create_group"
        simulated = $false
        name = $Name
        sam_account_name = $SamAccountName
        parent_dn = $ParentDn
        group_scope = $GroupScope
        group_category = $GroupCategory
        message = "Groupe créé"
    }
}

function Invoke-EitasAdAdminJob {
    param(
        [object]$Config,
        [object]$Job,
        [string]$Mode
    )

    $Action = Get-EitasAdAdminJobAction -Job $Job
    $Payload = Get-EitasAdAdminJobPayload -Job $Job

    if ([string]::IsNullOrWhiteSpace($Action)) {
        throw "Action AD Admin manquante"
    }

    switch ($Action) {
        "create_ou" {
            return Invoke-EitasAdAdminCreateOu -Config $Config -Payload $Payload -Mode $Mode
        }

        "create_group" {
            return Invoke-EitasAdAdminCreateGroup -Config $Config -Payload $Payload -Mode $Mode
        }

        default {
            throw "Action AD Admin non supportée : $Action"
        }
    }
}

function Process-EitasPendingAdAdminJobs {
    param(
        [object]$Config,
        [switch]$SilentWhenEmpty
    )

    $AgentName = Get-EitasAgentName -Config $Config

    $ModeResponse = Get-EitasAgentMode -Config $Config
    $Mode = [string]$ModeResponse.mode

    $Jobs = @(Get-EitasPendingAdAdminJobs -Config $Config)

    if ($Jobs.Count -eq 0) {
        if (-not $SilentWhenEmpty) {
            Write-EitasLog -Name "ad-admin-worker-light.log" -Level "INFO" -Message "Aucun job AD Admin en attente."
        }
        return 0
    }

    Write-EitasLog -Name "ad-admin-worker-light.log" -Level "INFO" -Message "Jobs AD Admin en attente : $($Jobs.Count)" -Console

    $Processed = 0

    foreach ($Job in $Jobs) {
        $JobId = Get-EitasAdAdminJobId -Job $Job

        if ([string]::IsNullOrWhiteSpace($JobId)) {
            Write-EitasLog -Name "ad-admin-worker-light.log" -Level "WARN" -Message "Job AD Admin sans ID ignoré." -Console
            continue
        }

        try {
            $Claim = Claim-EitasAdAdminJob -Config $Config -JobId $JobId -AgentName $AgentName

            if ($null -eq $Claim) {
                continue
            }

            $Result = Invoke-EitasAdAdminJob -Config $Config -Job $Job -Mode $Mode

            Send-EitasAdAdminJobResult `
                -Config $Config `
                -JobId $JobId `
                -Success $true `
                -Message $Result.message `
                -Output $Result `
                -AgentName $AgentName | Out-Null

            Write-EitasLog -Name "ad-admin-worker-light.log" -Level "OK" -Message "Job AD Admin terminé : $JobId / $($Result.message)" -Console

            $Processed++
        }
        catch {
            $ErrorMessage = $_.Exception.Message

            Write-EitasLog -Name "ad-admin-worker-light.log" -Level "ERROR" -Message "Job AD Admin échoué : $JobId / $ErrorMessage" -Console

            try {
                Send-EitasAdAdminJobResult `
                    -Config $Config `
                    -JobId $JobId `
                    -Success $false `
                    -Message $ErrorMessage `
                    -Output @{
                        action = Get-EitasAdAdminJobAction -Job $Job
                        error = $ErrorMessage
                    } `
                    -AgentName $AgentName | Out-Null
            }
            catch {
                Write-EitasLog -Name "ad-admin-worker-light.log" -Level "ERROR" -Message "Impossible d'envoyer le résultat erreur : $($_.Exception.Message)" -Console
            }
        }
    }

    return $Processed
}

