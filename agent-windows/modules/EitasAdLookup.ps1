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

function Convert-EitasAdDateValue {
    param([object]$Value)

    if ($null -eq $Value) {
        return $null
    }

    if ($Value -is [datetime]) {
        return $Value.ToString("yyyy-MM-dd HH:mm:ss")
    }

    return [string]$Value
}

function Convert-EitasAdBoolValue {
    param([object]$Value)

    if ($null -eq $Value) {
        return $null
    }

    if ($Value -is [bool]) {
        return [bool]$Value
    }

    $Text = ([string]$Value).Trim().ToLowerInvariant()

    if (@("true", "1", "yes", "oui") -contains $Text) {
        return $true
    }

    if (@("false", "0", "no", "non") -contains $Text) {
        return $false
    }

    return $Value
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
        enabled = Convert-EitasAdBoolValue -Value $User.Enabled
        locked_out = Convert-EitasAdBoolValue -Value $User.LockedOut
        password_expired = Convert-EitasAdBoolValue -Value $User.PasswordExpired
        password_never_expires = Convert-EitasAdBoolValue -Value $User.PasswordNeverExpires
        cannot_change_password = Convert-EitasAdBoolValue -Value $User.CannotChangePassword
        password_last_set = Convert-EitasAdDateValue -Value $User.PasswordLastSet
        last_logon = Convert-EitasAdDateValue -Value $User.LastLogonDate
        last_bad_password_attempt = Convert-EitasAdDateValue -Value $User.LastBadPasswordAttempt
        account_expires = Convert-EitasAdDateValue -Value $User.AccountExpirationDate
        bad_logon_count = $User.BadLogonCount
        department = $User.Department
        title = $User.Title
        company = $User.Company
        manager = $User.Manager
        office = $User.Office
        telephone_number = $User.TelephoneNumber
        mobile = $User.mobile
        city = $User.l
        country = $User.co
        state = $User.st
        postal_code = $User.postalCode
        street_address = $User.streetAddress
        employee_id = $User.employeeID
        employee_number = $User.employeeNumber
        division = $User.division
        member_of = @($User.MemberOf)
        object_guid = "$($User.ObjectGUID)"
        sid = if ($User.SID) { $User.SID.Value } else { $null }
        created_at = Convert-EitasAdDateValue $User.whenCreated
        updated_at = Convert-EitasAdDateValue $User.whenChanged
        canonical_name = $User.CanonicalName
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

    Assert-EitasDnSafe -DistinguishedName $SearchBase -Config $Config -AllowDomainRoot | Out-Null

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
        -Properties DisplayName, Mail, Enabled, Description, MemberOf, LockedOut, PasswordExpired, PasswordNeverExpires, CannotChangePassword, PasswordLastSet, LastLogonDate, LastBadPasswordAttempt, AccountExpirationDate, BadLogonCount, Department, Title, Company, Manager, Office, TelephoneNumber, ObjectGUID, SID, whenCreated, whenChanged, CanonicalName, l, co, st, postalCode, streetAddress, mobile, employeeID, employeeNumber, division `
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

function Get-EitasOuParentDn {
    param([string]$DistinguishedName)

    $Parts = @(([string]$DistinguishedName).Split(",") | ForEach-Object { $_.Trim() } | Where-Object { $_ })

    if ($Parts.Count -le 1) {
        return ""
    }

    return ($Parts[1..($Parts.Count - 1)] -join ",")
}

function Get-EitasOuPathLabel {
    param(
        [string]$DistinguishedName
    )

    $OuParts = @(([string]$DistinguishedName).Split(",") | Where-Object { $_ -match "^OU=" })

    if ($OuParts.Count -eq 0) {
        return $DistinguishedName
    }

    $Names = @($OuParts | ForEach-Object { ($_ -replace "^OU=", "").Trim() })
    [array]::Reverse($Names)

    return ($Names -join " / ")
}

function Get-EitasOuDepth {
    param([string]$DistinguishedName)

    return @(([string]$DistinguishedName).Split(",") | Where-Object { $_ -match "^OU=" }).Count - 1
}

function Convert-EitasAdOuTreeItem {
    param([object]$Ou)

    return [pscustomobject]@{
        type = "ou"
        name = $Ou.Name
        distinguished_name = $Ou.DistinguishedName
        dn = $Ou.DistinguishedName
        parent_dn = Get-EitasOuParentDn -DistinguishedName $Ou.DistinguishedName
        path_label = Get-EitasOuPathLabel -DistinguishedName $Ou.DistinguishedName
        depth = Get-EitasOuDepth -DistinguishedName $Ou.DistinguishedName
        description = $Ou.Description
    }
}

function Invoke-EitasAdExplorerListOuTree {
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

    $AllOus = @()

    if ($BaseDn -match "^OU=") {
        try {
            $BaseOu = Get-ADOrganizationalUnit `
                -Identity $BaseDn `
                -Properties Description `
                -ErrorAction Stop

            $AllOus += $BaseOu
        }
        catch {
            Write-EitasLog -Name "ad-lookup-worker-light.log" -Level "WARN" -Message "OU base non chargee directement : $BaseDn / $($_.Exception.Message)"
        }
    }

    $ChildOus = Get-ADOrganizationalUnit `
        -Filter * `
        -SearchBase $BaseDn `
        -SearchScope Subtree `
        -Properties Description `
        -ErrorAction Stop

    $AllOus += @($ChildOus)

    $Seen = @{}
    $Items = @()

    foreach ($Ou in $AllOus) {
        $Key = ([string]$Ou.DistinguishedName).ToUpperInvariant()

        if (-not $Seen.ContainsKey($Key)) {
            $Seen[$Key] = $true
            $Items += Convert-EitasAdOuTreeItem -Ou $Ou
        }
    }

    $Items = @($Items | Sort-Object path_label)

    return [pscustomobject]@{
        action = "list_ou_tree"
        base_dn = $BaseDn
        count = @($Items).Count
        items = @($Items)
        message = "Arbre des OU chargé"
    }
}

function Convert-EitasOuChildItem {
    param([object]$Object)

    return [pscustomobject]@{
        type = $Object.ObjectClass
        name = $Object.Name
        distinguished_name = $Object.DistinguishedName
        dn = $Object.DistinguishedName
    }
}

function Invoke-EitasAdExplorerCheckOuEmpty {
    param(
        [object]$Config,
        [object]$Payload
    )

    Import-EitasActiveDirectoryModule | Out-Null

    $OuDn = Get-EitasLookupValue -Object $Payload -Names @("ou_dn", "ouDn", "base_dn", "baseDn", "dn", "distinguished_name", "distinguishedName")

    if ([string]::IsNullOrWhiteSpace($OuDn)) {
        throw "DN de l'OU manquant"
    }

    $OuDn = ([string]$OuDn).Trim()

    if ($OuDn -notmatch "^OU=") {
        throw "La cible n'est pas une OU : $OuDn"
    }

    Assert-EitasDnSafe -DistinguishedName $OuDn -Config $Config -AllowDomainRoot | Out-Null

    Get-ADOrganizationalUnit `
        -Identity $OuDn `
        -ErrorAction Stop | Out-Null

    $Children = @(
        Get-ADObject `
            -SearchBase $OuDn `
            -SearchScope OneLevel `
            -Filter * `
            -Properties objectClass, distinguishedName, name `
            -ErrorAction Stop
    )

    $Items = @(
        $Children |
            Select-Object -First 50 |
            ForEach-Object {
                Convert-EitasOuChildItem -Object $_
            }
    )

    $IsEmpty = (@($Children).Count -eq 0)

    if ($IsEmpty) {
        $Message = "OU vide"
    } else {
        $Message = "OU non vide"
    }

    return [pscustomobject]@{
        action = "check_ou_empty"
        ou_dn = $OuDn
        is_empty = $IsEmpty
        child_count = @($Children).Count
        children = @($Items)
        message = $Message
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

    $RecursiveValue = Get-EitasLookupValue -Object $Payload -Names @("recursive", "Recursive", "recurse", "include_children", "includeChildren")
    $Recursive = $false

    if ($null -ne $RecursiveValue) {
        if ($RecursiveValue -is [bool]) {
            $Recursive = $RecursiveValue
        }
        else {
            $Recursive = @("1", "true", "yes", "oui", "subtree") -contains ([string]$RecursiveValue).Trim().ToLowerInvariant()
        }
    }

    $SearchScope = if ($Recursive) { "Subtree" } else { "OneLevel" }

    $Items = Get-ADGroup `
        -Filter * `
        -SearchBase $BaseDn `
        -SearchScope $SearchScope `
        -Properties Description `
        -ErrorAction Stop |
        Sort-Object Name |
        ForEach-Object { Convert-EitasAdGroupItem -Group $_ }

    return [pscustomobject]@{
        action = "list_groups"
        base_dn = $BaseDn
        recursive = $Recursive
        search_scope = $SearchScope
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

    $User = Get-ADUser -Identity $Identity -Properties DisplayName, Mail, Enabled, Description, MemberOf, LockedOut, PasswordExpired, PasswordNeverExpires, CannotChangePassword, PasswordLastSet, LastLogonDate, LastBadPasswordAttempt, AccountExpirationDate, BadLogonCount, Department, Title, Company, Manager, Office, TelephoneNumber, ObjectGUID, SID, whenCreated, whenChanged, CanonicalName, l, co, st, postalCode, streetAddress, mobile, employeeID, employeeNumber, division -ErrorAction Stop

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

    $Group = Get-ADGroup -Identity $Identity -Properties Description, ObjectGUID, SID, whenCreated, whenChanged, CanonicalName, GroupScope, GroupCategory, ManagedBy -ErrorAction Stop

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

        
        "list_ou_tree" {
            return Invoke-EitasAdExplorerListOuTree -Config $Config -Payload $Payload
        }


        "check_ou_empty" {
            return Invoke-EitasAdExplorerCheckOuEmpty -Config $Config -Payload $Payload
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

