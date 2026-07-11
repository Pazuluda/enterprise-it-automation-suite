function Get-EitasLookupValue {
    param(
        [object]$Object,
        [string[]]$Names
    )

    if ($null -eq $Object) { return $null }

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

function Get-EitasLookupItems {
    param([object]$Response)

    if ($null -eq $Response) { return @() }
    if ($Response -is [array]) { return @($Response) }

    foreach ($Name in @("jobs", "items", "data", "results", "pending")) {
        if ($Response.PSObject.Properties.Name -contains $Name -and $null -ne $Response.$Name) {
            return @($Response.$Name)
        }
    }

    return @($Response)
}

function Get-EitasLookupJobId {
    param([object]$Job)

    return Get-EitasLookupValue -Object $Job -Names @("id", "job_id", "jobId", "request_id")
}

function Get-EitasLookupPayload {
    param([object]$Job)

    $Payload = Get-EitasLookupValue -Object $Job -Names @("payload", "data", "parameters", "params")

    if ($null -eq $Payload) {
        return $Job
    }

    return $Payload
}

function Get-EitasLookupAction {
    param(
        [object]$Job,
        [string]$DefaultAction = "search_users"
    )

    $Payload = Get-EitasLookupPayload -Job $Job

    $Action = Get-EitasLookupValue -Object $Job -Names @("action", "type", "job_type")
    if ($Action) { return [string]$Action }

    $Action = Get-EitasLookupValue -Object $Payload -Names @("action", "type", "job_type")
    if ($Action) { return [string]$Action }

    return $DefaultAction
}

function Convert-EitasAdUserItem {
    param([object]$User)

    return [pscustomobject]@{
        type = "user"
        name = $User.Name
        display_name = $User.DisplayName
        sam_account_name = $User.SamAccountName
        user_principal_name = $User.UserPrincipalName
        mail = $User.Mail
        enabled = $User.Enabled
        distinguished_name = $User.DistinguishedName
        dn = $User.DistinguishedName
        description = $User.Description
    }
}

function Convert-EitasAdGroupItem {
    param([object]$Group)

    return [pscustomobject]@{
        type = "group"
        name = $Group.Name
        sam_account_name = $Group.SamAccountName
        group_scope = $Group.GroupScope
        group_category = $Group.GroupCategory
        distinguished_name = $Group.DistinguishedName
        dn = $Group.DistinguishedName
        description = $Group.Description
    }
}

function Convert-EitasAdOuItem {
    param([object]$Ou)

    return [pscustomobject]@{
        type = "ou"
        name = $Ou.Name
        distinguished_name = $Ou.DistinguishedName
        dn = $Ou.DistinguishedName
        description = $Ou.Description
    }
}

function Get-EitasDefaultUsersDn {
    param([object]$Config)

    return "OU=Users,$(Get-EitasAllowedBaseDn -Config $Config)"
}

function Get-EitasDefaultGroupsDn {
    param([object]$Config)

    return "OU=Groups,$(Get-EitasAllowedBaseDn -Config $Config)"
}

function Get-EitasPendingAdLookupJobs {
    param([object]$Config)

    $Response = Invoke-EitasApiRequest -Method "GET" -Path "/api/agent/ad-lookup/pending" -Config $Config
    return @(Get-EitasLookupItems -Response $Response)
}

function Claim-EitasAdLookupJob {
    param(
        [object]$Config,
        [string]$JobId,
        [string]$AgentName
    )

    try {
        return Invoke-EitasApiRequest `
            -Method "POST" `
            -Path "/api/agent/ad-lookup/claim/$JobId" `
            -Body @{
                agent_name = $AgentName
                processing_by = $AgentName
            } `
            -Config $Config
    }
    catch {
        $Message = $_.Exception.Message

        if ($Message -match "409|Conflict|non disponible|Statut actuel|déjà|deja") {
            Write-EitasLog -Name "ad-lookup-worker-light.log" -Level "WARN" -Message "Job AD Lookup déjà pris, ignoré : $JobId" -Console
            return $null
        }

        throw
    }
}

function Send-EitasAdLookupResult {
    param(
        [object]$Config,
        [string]$JobId,
        [bool]$Success,
        [string]$Message,
        [object]$Result,
        [string]$AgentName
    )

    return Invoke-EitasApiRequest `
        -Method "POST" `
        -Path "/api/agent/ad-lookup/result/$JobId" `
        -Body @{
            success = $Success
            message = $Message
            output = $Result
            result = $Result
            agent_name = $AgentName
            completed_by = $AgentName
        } `
        -Config $Config
}

function Invoke-EitasAdLookupJob {
    param(
        [object]$Config,
        [object]$Job
    )

    Import-EitasActiveDirectoryModule | Out-Null

    $Payload = Get-EitasLookupPayload -Job $Job

    $Query = Get-EitasLookupValue -Object $Payload -Names @("query", "search", "search_text", "text", "identity", "username", "sam_account_name", "samAccountName", "upn")
    $SearchBase = Get-EitasLookupValue -Object $Payload -Names @("search_base", "searchBase", "base_dn", "baseDn", "target_dn", "targetDn")

    if ([string]::IsNullOrWhiteSpace($SearchBase)) {
        $SearchBase = Get-EitasDefaultUsersDn -Config $Config
    }

    Assert-EitasDnSafe -DistinguishedName $SearchBase -Config $Config | Out-Null

    if ([string]::IsNullOrWhiteSpace($Query)) {
        $Filter = "(&(objectCategory=person)(objectClass=user))"
    }
    else {
        $Escaped = Escape-EitasLdapFilterValue -Value $Query
        $Filter = "(&(objectCategory=person)(objectClass=user)(|(sAMAccountName=*$Escaped*)(displayName=*$Escaped*)(userPrincipalName=*$Escaped*)(mail=*$Escaped*)))"
    }

    $Users = Get-ADUser `
        -LDAPFilter $Filter `
        -SearchBase $SearchBase `
        -SearchScope Subtree `
        -Properties DisplayName, Mail, Enabled, Description `
        -ResultSetSize 20 `
        -ErrorAction Stop |
        Sort-Object SamAccountName |
        ForEach-Object { Convert-EitasAdUserItem -User $_ }

    return [pscustomobject]@{
        action = "search_users"
        query = $Query
        search_base = $SearchBase
        count = @($Users).Count
        items = @($Users)
        message = "Recherche AD terminée"
    }
}

function Get-EitasPendingAdExplorerJobs {
    param([object]$Config)

    $Response = Invoke-EitasApiRequest -Method "GET" -Path "/api/agent/ad-explorer/pending" -Config $Config
    return @(Get-EitasLookupItems -Response $Response)
}

function Claim-EitasAdExplorerJob {
    param(
        [object]$Config,
        [string]$JobId,
        [string]$AgentName
    )

    try {
        return Invoke-EitasApiRequest `
            -Method "POST" `
            -Path "/api/agent/ad-explorer/claim/$JobId" `
            -Body @{
                agent_name = $AgentName
                processing_by = $AgentName
            } `
            -Config $Config
    }
    catch {
        $Message = $_.Exception.Message

        if ($Message -match "409|Conflict|non disponible|Statut actuel|déjà|deja") {
            Write-EitasLog -Name "ad-lookup-worker-light.log" -Level "WARN" -Message "Job AD Explorer déjà pris, ignoré : $JobId" -Console
            return $null
        }

        throw
    }
}

function Send-EitasAdExplorerResult {
    param(
        [object]$Config,
        [string]$JobId,
        [bool]$Success,
        [string]$Message,
        [object]$Result,
        [string]$AgentName
    )

    return Invoke-EitasApiRequest `
        -Method "POST" `
        -Path "/api/agent/ad-explorer/result/$JobId" `
        -Body @{
            success = $Success
            message = $Message
            output = $Result
            result = $Result
            agent_name = $AgentName
            completed_by = $AgentName
        } `
        -Config $Config
}

function Invoke-EitasAdExplorerListOus {
    param(
        [object]$Config,
        [object]$Payload
    )

    Import-EitasActiveDirectoryModule | Out-Null

    $BaseDn = Get-EitasLookupValue -Object $Payload -Names @("base_dn", "baseDn", "search_base", "searchBase", "target_dn", "targetDn", "dn")

    if ([string]::IsNullOrWhiteSpace($BaseDn)) {
        $BaseDn = Get-EitasAllowedBaseDn -Config $Config
    }

    Assert-EitasDnSafe -DistinguishedName $BaseDn -Config $Config -AllowDomainRoot | Out-Null

    $Items = Get-ADOrganizationalUnit `
        -Filter * `
        -SearchBase $BaseDn `
        -SearchScope OneLevel `
        -Properties Description `
        -ErrorAction Stop |
        Sort-Object Name |
        ForEach-Object { Convert-EitasAdOuItem -Ou $_ }

    return [pscustomobject]@{
        action = "list_ous"
        base_dn = $BaseDn
        count = @($Items).Count
        items = @($Items)
        message = "OU chargées"
    }
}

function Invoke-EitasAdExplorerListGroups {
    param(
        [object]$Config,
        [object]$Payload
    )

    Import-EitasActiveDirectoryModule | Out-Null

    $BaseDn = Get-EitasLookupValue -Object $Payload -Names @("base_dn", "baseDn", "search_base", "searchBase", "target_dn", "targetDn", "dn")

    if ([string]::IsNullOrWhiteSpace($BaseDn)) {
        $BaseDn = Get-EitasDefaultGroupsDn -Config $Config
    }

    Assert-EitasDnSafe -DistinguishedName $BaseDn -Config $Config | Out-Null

    $Items = Get-ADGroup `
        -Filter * `
        -SearchBase $BaseDn `
        -SearchScope OneLevel `
        -Properties Description `
        -ErrorAction Stop |
        Sort-Object Name |
        ForEach-Object { Convert-EitasAdGroupItem -Group $_ }

    return [pscustomobject]@{
        action = "list_groups"
        base_dn = $BaseDn
        count = @($Items).Count
        items = @($Items)
        message = "Groupes chargés"
    }
}

function Invoke-EitasAdExplorerSearchUsers {
    param(
        [object]$Config,
        [object]$Payload
    )

    $Result = Invoke-EitasAdLookupJob -Config $Config -Job $Payload
    $Result.action = "search_users"
    $Result.message = "Utilisateurs chargés"
    return $Result
}

function Invoke-EitasAdExplorerGetUser {
    param(
        [object]$Config,
        [object]$Payload
    )

    Import-EitasActiveDirectoryModule | Out-Null

    $Identity = Get-EitasLookupValue -Object $Payload -Names @("identity", "dn", "distinguished_name", "sam_account_name", "samAccountName", "upn")

    if ([string]::IsNullOrWhiteSpace($Identity)) {
        throw "Identité utilisateur manquante"
    }

    $User = Get-ADUser -Identity $Identity -Properties DisplayName, Mail, Enabled, Description, MemberOf -ErrorAction Stop

    Assert-EitasDnSafe -DistinguishedName $User.DistinguishedName -Config $Config | Out-Null

    return [pscustomobject]@{
        action = "get_user"
        item = Convert-EitasAdUserItem -User $User
        member_of = @($User.MemberOf)
        message = "Utilisateur chargé"
    }
}

function Invoke-EitasAdExplorerGetGroupMembers {
    param(
        [object]$Config,
        [object]$Payload
    )

    Import-EitasActiveDirectoryModule | Out-Null

    $Identity = Get-EitasLookupValue -Object $Payload -Names @(
        "query",
        "search",
        "identity",
        "group_identity",
        "group_name",
        "dn",
        "distinguished_name",
        "sam_account_name",
        "samAccountName",
        "name"
    )

    if ([string]::IsNullOrWhiteSpace($Identity)) {
        $Filters = Get-EitasLookupValue -Object $Payload -Names @("filters")

        if ($null -ne $Filters) {
            $Identity = Get-EitasLookupValue -Object $Filters -Names @(
                "query",
                "identity",
                "group_identity",
                "group_name",
                "dn",
                "distinguished_name",
                "sam_account_name",
                "samAccountName",
                "name"
            )
        }
    }

    if ([string]::IsNullOrWhiteSpace($Identity)) {
        throw "Identité groupe manquante"
    }

    $Group = Get-ADGroup -Identity $Identity -Properties Description -ErrorAction Stop

    Assert-EitasDnSafe -DistinguishedName $Group.DistinguishedName -Config $Config | Out-Null

    $Members = Get-ADGroupMember -Identity $Group.DistinguishedName -ErrorAction Stop |
        Sort-Object Name |
        ForEach-Object {
            [pscustomobject]@{
                type = $_.objectClass
                name = $_.Name
                sam_account_name = $_.SamAccountName
                distinguished_name = $_.DistinguishedName
                dn = $_.DistinguishedName
            }
        }

    return [pscustomobject]@{
        action = "get_group_members"
        group = Convert-EitasAdGroupItem -Group $Group
        count = @($Members).Count
        items = @($Members)
        message = "Membres du groupe chargés"
    }
}

function Invoke-EitasAdExplorerJob {
    param(
        [object]$Config,
        [object]$Job
    )

    $Action = Get-EitasLookupAction -Job $Job -DefaultAction "list_ous"
    $Payload = Get-EitasLookupPayload -Job $Job

    switch ($Action) {
        "list_ous" {
            return Invoke-EitasAdExplorerListOus -Config $Config -Payload $Payload
        }

        "list_groups" {
            return Invoke-EitasAdExplorerListGroups -Config $Config -Payload $Payload
        }

        "search_users" {
            return Invoke-EitasAdExplorerSearchUsers -Config $Config -Payload $Payload
        }

        "get_user" {
            return Invoke-EitasAdExplorerGetUser -Config $Config -Payload $Payload
        }

        "get_group_members" {
            return Invoke-EitasAdExplorerGetGroupMembers -Config $Config -Payload $Payload
        }

        default {
            throw "Action AD Explorer non supportée : $Action"
        }
    }
}

function Process-EitasPendingAdLookupJobs {
    param(
        [object]$Config,
        [switch]$SilentWhenEmpty
    )

    $AgentName = Get-EitasAgentName -Config $Config
    $Jobs = @(Get-EitasPendingAdLookupJobs -Config $Config)

    if ($Jobs.Count -eq 0) {
        if (-not $SilentWhenEmpty) {
            Write-EitasLog -Name "ad-lookup-worker-light.log" -Level "INFO" -Message "Aucun job AD Lookup en attente."
        }
        return 0
    }

    Write-EitasLog -Name "ad-lookup-worker-light.log" -Level "INFO" -Message "Jobs AD Lookup en attente : $($Jobs.Count)" -Console

    $Processed = 0

    foreach ($Job in $Jobs) {
        $JobId = Get-EitasLookupJobId -Job $Job

        try {
            $Claim = Claim-EitasAdLookupJob -Config $Config -JobId $JobId -AgentName $AgentName
            if ($null -eq $Claim) { continue }

            $Result = Invoke-EitasAdLookupJob -Config $Config -Job $Job

            Send-EitasAdLookupResult -Config $Config -JobId $JobId -Success $true -Message $Result.message -Result $Result -AgentName $AgentName | Out-Null

            Write-EitasLog -Name "ad-lookup-worker-light.log" -Level "OK" -Message "Job AD Lookup terminé : $JobId / $($Result.message)" -Console
            $Processed++
        }
        catch {
            $ErrorMessage = $_.Exception.Message

            Write-EitasLog -Name "ad-lookup-worker-light.log" -Level "ERROR" -Message "Job AD Lookup échoué : $JobId / $ErrorMessage" -Console

            try {
                Send-EitasAdLookupResult -Config $Config -JobId $JobId -Success $false -Message $ErrorMessage -Result @{ error = $ErrorMessage } -AgentName $AgentName | Out-Null
            }
            catch {}
        }
    }

    return $Processed
}

function Process-EitasPendingAdExplorerJobs {
    param(
        [object]$Config,
        [switch]$SilentWhenEmpty
    )

    $AgentName = Get-EitasAgentName -Config $Config
    $Jobs = @(Get-EitasPendingAdExplorerJobs -Config $Config)

    if ($Jobs.Count -eq 0) {
        if (-not $SilentWhenEmpty) {
            Write-EitasLog -Name "ad-lookup-worker-light.log" -Level "INFO" -Message "Aucun job AD Explorer en attente."
        }
        return 0
    }

    Write-EitasLog -Name "ad-lookup-worker-light.log" -Level "INFO" -Message "Jobs AD Explorer en attente : $($Jobs.Count)" -Console

    $Processed = 0

    foreach ($Job in $Jobs) {
        $JobId = Get-EitasLookupJobId -Job $Job

        try {
            $Claim = Claim-EitasAdExplorerJob -Config $Config -JobId $JobId -AgentName $AgentName
            if ($null -eq $Claim) { continue }

            $Result = Invoke-EitasAdExplorerJob -Config $Config -Job $Job

            Send-EitasAdExplorerResult -Config $Config -JobId $JobId -Success $true -Message $Result.message -Result $Result -AgentName $AgentName | Out-Null

            Write-EitasLog -Name "ad-lookup-worker-light.log" -Level "OK" -Message "Job AD Explorer terminé : $JobId / $($Result.message)" -Console
            $Processed++
        }
        catch {
            $ErrorMessage = $_.Exception.Message

            Write-EitasLog -Name "ad-lookup-worker-light.log" -Level "ERROR" -Message "Job AD Explorer échoué : $JobId / $ErrorMessage" -Console

            try {
                Send-EitasAdExplorerResult -Config $Config -JobId $JobId -Success $false -Message $ErrorMessage -Result @{ error = $ErrorMessage } -AgentName $AgentName | Out-Null
            }
            catch {}
        }
    }

    return $Processed
}

