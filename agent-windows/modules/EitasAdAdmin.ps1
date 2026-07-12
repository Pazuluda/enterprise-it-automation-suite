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


function Resolve-EitasAdAdminGroup {
    param(
        [object]$Config,
        [string]$Identity
    )

    if ([string]::IsNullOrWhiteSpace($Identity)) {
        throw "Identité groupe manquante"
    }

    Import-EitasActiveDirectoryModule | Out-Null

    $Group = Get-ADGroup -Identity $Identity -Properties Description -ErrorAction Stop
    Assert-EitasDnSafe -DistinguishedName $Group.DistinguishedName -Config $Config | Out-Null

    return $Group
}

function Resolve-EitasAdAdminMember {
    param(
        [object]$Config,
        [string]$Identity
    )

    if ([string]::IsNullOrWhiteSpace($Identity)) {
        throw "Identité membre manquante"
    }

    Import-EitasActiveDirectoryModule | Out-Null

    $AllowedBaseDn = Get-EitasAllowedBaseDn -Config $Config
    $Object = $null

    if ($Identity -match "^(CN|OU|DC)=") {
        $Object = Get-ADObject `
            -Identity $Identity `
            -Properties objectClass, sAMAccountName, userPrincipalName, displayName, description `
            -ErrorAction Stop
    }
    else {
        $Escaped = Escape-EitasLdapFilterValue -Value $Identity

        $Matches = @(Get-ADObject `
            -LDAPFilter "(|(sAMAccountName=$Escaped)(userPrincipalName=$Escaped)(cn=$Escaped)(name=$Escaped))" `
            -SearchBase $AllowedBaseDn `
            -SearchScope Subtree `
            -Properties objectClass, sAMAccountName, userPrincipalName, displayName, description `
            -ResultSetSize 5 `
            -ErrorAction Stop)

        if ($Matches.Count -eq 0) {
            throw "Membre introuvable : $Identity"
        }

        if ($Matches.Count -gt 1) {
            throw "Plusieurs objets AD correspondent au membre : $Identity"
        }

        $Object = $Matches[0]
    }

    Assert-EitasDnSafe -DistinguishedName $Object.DistinguishedName -Config $Config | Out-Null

    return $Object
}

function Convert-EitasAdAdminObjectItem {
    param([object]$Object)

    return [pscustomobject]@{
        type = $Object.ObjectClass
        name = $Object.Name
        sam_account_name = $Object.SamAccountName
        user_principal_name = $Object.UserPrincipalName
        distinguished_name = $Object.DistinguishedName
        dn = $Object.DistinguishedName
    }
}

function Invoke-EitasAdAdminAddGroupMember {
    param(
        [object]$Config,
        [object]$Payload,
        [string]$Mode
    )

    $GroupIdentity = Get-EitasObjectValue -Object $Payload -Names @("group_identity", "groupIdentity", "group_dn", "groupDn", "group_name", "groupName", "group")
    $MemberIdentity = Get-EitasObjectValue -Object $Payload -Names @("member_identity", "memberIdentity", "member_dn", "memberDn", "member_name", "memberName", "member", "user_identity", "username", "sam_account_name", "samAccountName")

    if ([string]::IsNullOrWhiteSpace($GroupIdentity)) {
        throw "Identité groupe manquante"
    }

    if ([string]::IsNullOrWhiteSpace($MemberIdentity)) {
        throw "Identité membre manquante"
    }

    if ($Mode -ne "Production") {
        return [pscustomobject]@{
            action = "add_group_member"
            simulated = $true
            group_identity = $GroupIdentity
            member_identity = $MemberIdentity
            message = "Simulation ajout membre groupe"
        }
    }

    $Group = Resolve-EitasAdAdminGroup -Config $Config -Identity $GroupIdentity
    $Member = Resolve-EitasAdAdminMember -Config $Config -Identity $MemberIdentity

    $Existing = @(Get-ADGroupMember -Identity $Group.DistinguishedName -ErrorAction Stop |
        Where-Object { $_.DistinguishedName -ieq $Member.DistinguishedName })

    if ($Existing.Count -gt 0) {
        return [pscustomobject]@{
            action = "add_group_member"
            simulated = $false
            already_member = $true
            group = $Group.Name
            member = $Member.Name
            group_dn = $Group.DistinguishedName
            member_dn = $Member.DistinguishedName
            message = "Le membre est déjà dans le groupe"
        }
    }

    Add-ADGroupMember `
        -Identity $Group.DistinguishedName `
        -Members $Member.DistinguishedName `
        -ErrorAction Stop

    return [pscustomobject]@{
        action = "add_group_member"
        simulated = $false
        already_member = $false
        group = $Group.Name
        member = $Member.Name
        group_dn = $Group.DistinguishedName
        member_dn = $Member.DistinguishedName
        member_object = Convert-EitasAdAdminObjectItem -Object $Member
        message = "Membre ajouté au groupe"
    }
}

function Invoke-EitasAdAdminRemoveGroupMember {
    param(
        [object]$Config,
        [object]$Payload,
        [string]$Mode
    )

    $GroupIdentity = Get-EitasObjectValue -Object $Payload -Names @("group_identity", "groupIdentity", "group_dn", "groupDn", "group_name", "groupName", "group")
    $MemberIdentity = Get-EitasObjectValue -Object $Payload -Names @("member_identity", "memberIdentity", "member_dn", "memberDn", "member_name", "memberName", "member", "user_identity", "username", "sam_account_name", "samAccountName")

    if ([string]::IsNullOrWhiteSpace($GroupIdentity)) {
        throw "Identité groupe manquante"
    }

    if ([string]::IsNullOrWhiteSpace($MemberIdentity)) {
        throw "Identité membre manquante"
    }

    if ($Mode -ne "Production") {
        return [pscustomobject]@{
            action = "remove_group_member"
            simulated = $true
            group_identity = $GroupIdentity
            member_identity = $MemberIdentity
            message = "Simulation retrait membre groupe"
        }
    }

    $Group = Resolve-EitasAdAdminGroup -Config $Config -Identity $GroupIdentity
    $Member = Resolve-EitasAdAdminMember -Config $Config -Identity $MemberIdentity

    $Existing = @(Get-ADGroupMember -Identity $Group.DistinguishedName -ErrorAction Stop |
        Where-Object { $_.DistinguishedName -ieq $Member.DistinguishedName })

    if ($Existing.Count -eq 0) {
        return [pscustomobject]@{
            action = "remove_group_member"
            simulated = $false
            was_member = $false
            group = $Group.Name
            member = $Member.Name
            group_dn = $Group.DistinguishedName
            member_dn = $Member.DistinguishedName
            message = "Le membre n’était pas dans le groupe"
        }
    }

    Remove-ADGroupMember `
        -Identity $Group.DistinguishedName `
        -Members $Member.DistinguishedName `
        -Confirm:$false `
        -ErrorAction Stop

    return [pscustomobject]@{
        action = "remove_group_member"
        simulated = $false
        was_member = $true
        group = $Group.Name
        member = $Member.Name
        group_dn = $Group.DistinguishedName
        member_dn = $Member.DistinguishedName
        member_object = Convert-EitasAdAdminObjectItem -Object $Member
        message = "Membre retiré du groupe"
    }
}



function Resolve-EitasAdAdminObject {
    param(
        [object]$Config,
        [string]$Identity
    )

    if ([string]::IsNullOrWhiteSpace($Identity)) {
        throw "Identité objet AD manquante"
    }

    $Object = $null

    try {
        $Object = Get-ADObject `
            -Identity $Identity `
            -Properties objectClass, sAMAccountName, userPrincipalName, displayName, description `
            -ErrorAction Stop
    }
    catch {
        $Object = $null
    }

    if ($null -eq $Object) {
        $SearchBase = Get-EitasObjectValue -Object $Config -Names @("AdBaseDn", "BaseDn", "DomainDn")
        $SafeIdentity = $Identity.Replace("\", "\5c").Replace("*", "\2a").Replace("(", "\28").Replace(")", "\29")

        $Matches = @(Get-ADObject `
            -LDAPFilter "(|(name=$SafeIdentity)(sAMAccountName=$SafeIdentity)(displayName=$SafeIdentity))" `
            -SearchBase $SearchBase `
            -Properties objectClass, sAMAccountName, userPrincipalName, displayName, description `
            -ResultSetSize 5 `
            -ErrorAction Stop)

        if ($Matches.Count -eq 0) {
            throw "Objet AD introuvable : $Identity"
        }

        if ($Matches.Count -gt 1) {
            throw "Plusieurs objets AD correspondent à : $Identity"
        }

        $Object = $Matches[0]
    }

    Assert-EitasDnSafe -DistinguishedName $Object.DistinguishedName -Config $Config | Out-Null

    return $Object
}





function Repair-EitasTextEncoding {
    param(
        [object]$Value
    )

    if ($null -eq $Value) {
        return $null
    }

    $Text = [string]$Value

    # Corrige les textes UTF-8 lus comme Windows-1252 :
    # exemple : modifiÃ©e -> modifiée
    if ($Text.IndexOf([char]0x00C3) -ge 0 -or $Text.IndexOf([char]0x00C2) -ge 0) {
        try {
            $Bytes = [System.Text.Encoding]::GetEncoding(1252).GetBytes($Text)
            return [System.Text.Encoding]::UTF8.GetString($Bytes)
        } catch {
            return $Text
        }
    }

    return $Text
}


function Invoke-EitasAdAdminUpdateObjectProperties {
    param(
        [object]$Config,
        [object]$Payload,
        [string]$Mode
    )

    $ObjectIdentity = Get-EitasObjectValue -Object $Payload -Names @(
        "object_identity",
        "objectIdentity",
        "object_dn",
        "objectDn",
        "distinguished_name",
        "distinguishedName",
        "dn",
        "sam_account_name",
        "samAccountName",
        "name"
    )

    $PropertiesObject = Get-EitasObjectValue -Object $Payload -Names @(
        "properties",
        "Properties"
    )

    if ([string]::IsNullOrWhiteSpace($ObjectIdentity)) {
        throw "Identité objet AD manquante"
    }

    if ($null -eq $PropertiesObject) {
        throw "Propriétés à modifier manquantes"
    }

    $AllowedProperties = @(
        "description",
        "displayName",
        "mail",
        "title",
        "department",
        "company",
        "telephoneNumber",
        "physicalDeliveryOfficeName"
    )

    $Properties = @{}

    if ($PropertiesObject -is [System.Collections.IDictionary]) {
        foreach ($Key in $PropertiesObject.Keys) {
            $Properties[[string]$Key] = $PropertiesObject[$Key]
        }
    } else {
        foreach ($Property in $PropertiesObject.PSObject.Properties) {
            $Properties[[string]$Property.Name] = $Property.Value
        }
    }

    if ($Properties.Count -lt 1) {
        throw "Aucune propriété à modifier"
    }

    foreach ($Key in $Properties.Keys) {
        if ($AllowedProperties -notcontains $Key) {
            throw "Attribut non autorisé côté agent : $Key"
        }
    }

    if ($Mode -ne "Production") {
        return [pscustomobject]@{
            action = "update_object_properties"
            simulated = $true
            object_identity = $ObjectIdentity
            properties = $Properties
            message = "Simulation modification propriétés objet AD"
        }
    }

    $Object = Resolve-EitasAdAdminObject -Config $Config -Identity $ObjectIdentity
    $ObjectDn = ([string]$Object.DistinguishedName).Trim()

    $Replace = @{}
    $Clear = @()

    foreach ($Key in $Properties.Keys) {
        $Value = Repair-EitasTextEncoding -Value $Properties[$Key]

        if ($null -eq $Value -or [string]::IsNullOrWhiteSpace([string]$Value)) {
            $Clear += $Key
        } else {
            $Replace[$Key] = [string]$Value
        }
    }

    if ($Replace.Count -gt 0) {
        Set-ADObject `
            -Identity $ObjectDn `
            -Replace $Replace `
            -ErrorAction Stop
    }

    if ($Clear.Count -gt 0) {
        Set-ADObject `
            -Identity $ObjectDn `
            -Clear $Clear `
            -ErrorAction Stop
    }

    $UpdatedObject = Get-ADObject `
        -Identity $ObjectDn `
        -Properties objectClass, sAMAccountName, userPrincipalName, displayName, description, mail, title, department, company, telephoneNumber, physicalDeliveryOfficeName `
        -ErrorAction Stop

    return [pscustomobject]@{
        action = "update_object_properties"
        simulated = $false
        object = $Object.Name
        object_type = $Object.ObjectClass
        object_dn = $ObjectDn
        replaced = $Replace
        cleared = $Clear
        updated_object = Convert-EitasAdAdminObjectItem -Object $UpdatedObject
        message = "Propriétés objet AD modifiées"
    }
}


function Invoke-EitasAdAdminDeleteObject {
    param(
        [object]$Config,
        [object]$Payload,
        [string]$Mode
    )

    $ObjectIdentity = Get-EitasObjectValue -Object $Payload -Names @(
        "object_identity",
        "objectIdentity",
        "object_dn",
        "objectDn",
        "distinguished_name",
        "distinguishedName",
        "dn",
        "sam_account_name",
        "samAccountName",
        "name"
    )

    $ConfirmDn = Get-EitasObjectValue -Object $Payload -Names @(
        "confirm_dn",
        "confirmDn",
        "confirmation_dn",
        "confirmationDn"
    )

    if ([string]::IsNullOrWhiteSpace($ObjectIdentity)) {
        throw "Identité objet AD manquante"
    }

    if ([string]::IsNullOrWhiteSpace($ConfirmDn)) {
        throw "DN de confirmation manquant"
    }

    $ConfirmDn = ([string]$ConfirmDn).Trim()

    if ($Mode -ne "Production") {
        return [pscustomobject]@{
            action = "delete_object"
            simulated = $true
            object_identity = $ObjectIdentity
            confirm_dn = $ConfirmDn
            message = "Simulation suppression objet AD"
        }
    }

    $Object = Resolve-EitasAdAdminObject -Config $Config -Identity $ObjectIdentity

    $ObjectDn = ([string]$Object.DistinguishedName).Trim()

    if ($ObjectDn -ine $ConfirmDn) {
        throw "Confirmation DN invalide. DN réel : $ObjectDn"
    }

    $DeletedObject = Convert-EitasAdAdminObjectItem -Object $Object

    Remove-ADObject `
        -Identity $ObjectDn `
        -Confirm:$false `
        -ErrorAction Stop

    return [pscustomobject]@{
        action = "delete_object"
        simulated = $false
        object = $Object.Name
        object_type = $Object.ObjectClass
        object_dn = $ObjectDn
        confirm_dn = $ConfirmDn
        deleted_object = $DeletedObject
        message = "Objet AD supprimé"
    }
}


function Invoke-EitasAdAdminRenameObject {
    param(
        [object]$Config,
        [object]$Payload,
        [string]$Mode
    )

    $ObjectIdentity = Get-EitasObjectValue -Object $Payload -Names @(
        "object_identity",
        "objectIdentity",
        "object_dn",
        "objectDn",
        "distinguished_name",
        "distinguishedName",
        "dn",
        "sam_account_name",
        "samAccountName",
        "name"
    )

    $NewName = Get-EitasObjectValue -Object $Payload -Names @(
        "new_name",
        "newName",
        "target_name",
        "targetName"
    )

    if ([string]::IsNullOrWhiteSpace($ObjectIdentity)) {
        throw "Identité objet AD manquante"
    }

    if ([string]::IsNullOrWhiteSpace($NewName)) {
        throw "Nouveau nom manquant"
    }

    $NewName = ([string]$NewName).Trim()

    if ($Mode -ne "Production") {
        return [pscustomobject]@{
            action = "rename_object"
            simulated = $true
            object_identity = $ObjectIdentity
            new_name = $NewName
            message = "Simulation renommage objet AD"
        }
    }

    $Object = Resolve-EitasAdAdminObject -Config $Config -Identity $ObjectIdentity

    $ObjectDn = [string]$Object.DistinguishedName
    $CommaIndex = $ObjectDn.IndexOf(",")

    if ($CommaIndex -lt 1) {
        throw "DN objet invalide : $ObjectDn"
    }

    $CurrentRdn = $ObjectDn.Substring(0, $CommaIndex)
    $CurrentParentDn = $ObjectDn.Substring($CommaIndex + 1)
    $RdnPrefix = $CurrentRdn.Split("=")[0]
    $CurrentName = $CurrentRdn.Substring($RdnPrefix.Length + 1)
    $NewDn = "$RdnPrefix=$NewName,$CurrentParentDn"

    if ($CurrentName -ieq $NewName) {
        return [pscustomobject]@{
            action = "rename_object"
            simulated = $false
            already_named = $true
            object = $Object.Name
            object_type = $Object.ObjectClass
            object_dn = $ObjectDn
            old_name = $CurrentName
            new_name = $NewName
            new_dn = $ObjectDn
            message = "L’objet porte déjà ce nom"
        }
    }

    Rename-ADObject `
        -Identity $ObjectDn `
        -NewName $NewName `
        -ErrorAction Stop

    $RenamedObject = Get-ADObject `
        -Identity $NewDn `
        -Properties objectClass, sAMAccountName, userPrincipalName, displayName, description `
        -ErrorAction Stop

    return [pscustomobject]@{
        action = "rename_object"
        simulated = $false
        already_named = $false
        object = $Object.Name
        object_type = $Object.ObjectClass
        object_dn = $ObjectDn
        old_name = $CurrentName
        new_name = $NewName
        new_dn = $RenamedObject.DistinguishedName
        renamed_object = Convert-EitasAdAdminObjectItem -Object $RenamedObject
        message = "Objet AD renommé"
    }
}


function Invoke-EitasAdAdminMoveObject {
    param(
        [object]$Config,
        [object]$Payload,
        [string]$Mode
    )

    $ObjectIdentity = Get-EitasObjectValue -Object $Payload -Names @(
        "object_identity",
        "objectIdentity",
        "object_dn",
        "objectDn",
        "distinguished_name",
        "distinguishedName",
        "dn",
        "sam_account_name",
        "samAccountName",
        "name"
    )

    $TargetParentDn = Get-EitasObjectValue -Object $Payload -Names @(
        "target_parent_dn",
        "targetParentDn",
        "target_ou_dn",
        "targetOuDn",
        "target_dn",
        "targetDn"
    )

    if ([string]::IsNullOrWhiteSpace($ObjectIdentity)) {
        throw "Identité objet AD manquante"
    }

    if ([string]::IsNullOrWhiteSpace($TargetParentDn)) {
        throw "DN destination manquant"
    }

    if ($Mode -ne "Production") {
        return [pscustomobject]@{
            action = "move_object"
            simulated = $true
            object_identity = $ObjectIdentity
            target_parent_dn = $TargetParentDn
            message = "Simulation déplacement objet AD"
        }
    }

    $Object = Resolve-EitasAdAdminObject -Config $Config -Identity $ObjectIdentity

    Assert-EitasDnSafe -DistinguishedName $TargetParentDn -Config $Config | Out-Null

    $TargetParent = Get-ADObject `
        -Identity $TargetParentDn `
        -Properties objectClass, distinguishedName, name `
        -ErrorAction Stop

    Assert-EitasDnSafe -DistinguishedName $TargetParent.DistinguishedName -Config $Config | Out-Null

    $ObjectDn = [string]$Object.DistinguishedName
    $TargetDn = [string]$TargetParent.DistinguishedName

    if ($TargetDn -ieq $ObjectDn -or $TargetDn.ToLowerInvariant().EndsWith("," + $ObjectDn.ToLowerInvariant())) {
        throw "Déplacement impossible : la destination est l’objet lui-même ou un de ses enfants"
    }

    $CommaIndex = $ObjectDn.IndexOf(",")
    if ($CommaIndex -lt 1) {
        throw "DN objet invalide : $ObjectDn"
    }

    $ObjectRdn = $ObjectDn.Substring(0, $CommaIndex)
    $CurrentParentDn = $ObjectDn.Substring($CommaIndex + 1)
    $NewDn = "$ObjectRdn,$TargetDn"

    if ($CurrentParentDn -ieq $TargetDn) {
        return [pscustomobject]@{
            action = "move_object"
            simulated = $false
            already_in_target = $true
            object = $Object.Name
            object_type = $Object.ObjectClass
            object_dn = $ObjectDn
            old_parent_dn = $CurrentParentDn
            target_parent_dn = $TargetDn
            new_dn = $ObjectDn
            message = "L’objet est déjà dans cette destination"
        }
    }

    Move-ADObject `
        -Identity $ObjectDn `
        -TargetPath $TargetDn `
        -ErrorAction Stop

    return [pscustomobject]@{
        action = "move_object"
        simulated = $false
        already_in_target = $false
        object = $Object.Name
        object_type = $Object.ObjectClass
        object_dn = $ObjectDn
        old_parent_dn = $CurrentParentDn
        target_parent_dn = $TargetDn
        new_dn = $NewDn
        message = "Objet AD déplacé"
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

        "add_group_member" {
            return Invoke-EitasAdAdminAddGroupMember -Config $Config -Payload $Payload -Mode $Mode
        }

        "remove_group_member" {
            return Invoke-EitasAdAdminRemoveGroupMember -Config $Config -Payload $Payload -Mode $Mode
        }

        "move_object" {
            return Invoke-EitasAdAdminMoveObject -Config $Config -Payload $Payload -Mode $Mode
        }

        "rename_object" {
            return Invoke-EitasAdAdminRenameObject -Config $Config -Payload $Payload -Mode $Mode
        }

        "delete_object" {
            return Invoke-EitasAdAdminDeleteObject -Config $Config -Payload $Payload -Mode $Mode
        }

        "update_object_properties" {
            return Invoke-EitasAdAdminUpdateObjectProperties -Config $Config -Payload $Payload -Mode $Mode
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

