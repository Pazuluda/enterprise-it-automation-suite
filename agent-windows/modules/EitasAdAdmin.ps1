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
        $Params.Description =
            Repair-EitasTextEncoding -Value $Description
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
        $Params.Description =
            Repair-EitasTextEncoding -Value $Description
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

function Invoke-EitasAdAdminCreateUser {
    param(
        [object]$Config,
        [object]$Payload,
        [string]$Mode
    )

    $FirstName = Get-EitasObjectValue `
        -Object $Payload `
        -Names @(
            "first_name",
            "firstName",
            "given_name",
            "givenName"
        )

    $LastName = Get-EitasObjectValue `
        -Object $Payload `
        -Names @(
            "last_name",
            "lastName",
            "surname",
            "sn"
        )

    $SamAccountName = Get-EitasObjectValue `
        -Object $Payload `
        -Names @(
            "sam_account_name",
            "samAccountName",
            "username",
            "login"
        )

    $UserPrincipalName = Get-EitasObjectValue `
        -Object $Payload `
        -Names @(
            "user_principal_name",
            "userPrincipalName",
            "upn"
        )

    $TargetOuDn = Get-EitasObjectValue `
        -Object $Payload `
        -Names @(
            "target_ou_dn",
            "targetOuDn",
            "target_parent_dn",
            "targetParentDn",
            "ou_dn",
            "ouDn"
        )

    $TemporaryPassword = Get-EitasObjectValue `
        -Object $Payload `
        -Names @(
            "temporary_password",
            "temporaryPassword",
            "password"
        )

    $Description = Get-EitasObjectValue `
        -Object $Payload `
        -Names @(
            "description",
            "Description"
        )

    $EnabledValue = Get-EitasObjectValue `
        -Object $Payload `
        -Names @(
            "enabled",
            "Enabled"
        )

    $ForceChangeValue = Get-EitasObjectValue `
        -Object $Payload `
        -Names @(
            "force_change_at_logon",
            "change_password_at_logon",
            "changePasswordAtLogon"
        )

    if (
        [string]::IsNullOrWhiteSpace(
            [string]$FirstName
        )
    ) {
        throw "Prénom utilisateur manquant"
    }

    if (
        [string]::IsNullOrWhiteSpace(
            [string]$LastName
        )
    ) {
        throw "Nom utilisateur manquant"
    }

    if (
        [string]::IsNullOrWhiteSpace(
            [string]$SamAccountName
        )
    ) {
        throw "Identifiant utilisateur manquant"
    }

    if (
        [string]::IsNullOrWhiteSpace(
            [string]$TargetOuDn
        )
    ) {
        throw "OU cible manquante"
    }

    if (
        [string]::IsNullOrWhiteSpace(
            [string]$TemporaryPassword
        )
    ) {
        throw "Mot de passe temporaire manquant"
    }

    $FirstName = Repair-EitasTextEncoding `
        -Value ([string]$FirstName).Trim()

    $LastName = Repair-EitasTextEncoding `
        -Value ([string]$LastName).Trim()

    $SamAccountName = (
        [string]$SamAccountName
    ).Trim()

    $TargetOuDn = (
        [string]$TargetOuDn
    ).Trim()

    $Description = Repair-EitasTextEncoding `
        -Value ([string]$Description).Trim()

    if ($SamAccountName.Length -gt 20) {
        throw "Identifiant utilisateur limité à 20 caractères"
    }

    if ($SamAccountName -notmatch "^[A-Za-z0-9._-]+$") {
        throw "Format identifiant utilisateur invalide"
    }

    if (
        [string]::IsNullOrWhiteSpace(
            [string]$UserPrincipalName
        )
    ) {
        $DomainParts = @(
            $TargetOuDn -split "," |
                ForEach-Object {
                    ([string]$_).Trim()
                } |
                Where-Object {
                    $_ -match "^DC="
                } |
                ForEach-Object {
                    $_.Substring(3)
                }
        )

        $DomainDnsName = (
            $DomainParts -join "."
        )

        if (
            [string]::IsNullOrWhiteSpace(
                $DomainDnsName
            )
        ) {
            throw "Domaine UPN impossible à déterminer"
        }

        $UserPrincipalName =
            "$SamAccountName@$DomainDnsName"
    } else {
        $UserPrincipalName = (
            [string]$UserPrincipalName
        ).Trim()
    }

    if ($UserPrincipalName -notmatch "^[A-Za-z0-9._-]+@[A-Za-z0-9.-]+$") {
        throw "UPN utilisateur invalide"
    }

    Assert-EitasDnSafe `
        -DistinguishedName $TargetOuDn `
        -Config $Config |
        Out-Null

    $Enabled = Convert-EitasAdAdminBool `
        -Value $EnabledValue `
        -Default $false

    $ForceChangeAtLogon = Convert-EitasAdAdminBool `
        -Value $ForceChangeValue `
        -Default $true

    $DisplayName = "$FirstName $LastName"
    $Name = $DisplayName

    if ($Mode -ne "Production") {
        return [pscustomobject]@{
            action = "create_user"
            simulated = $true
            first_name = $FirstName
            last_name = $LastName
            display_name = $DisplayName
            sam_account_name = $SamAccountName
            user_principal_name = $UserPrincipalName
            target_ou_dn = $TargetOuDn
            enabled = $Enabled
            force_change_at_logon = $ForceChangeAtLogon
            description = $Description
            message = "Simulation création utilisateur AD"
        }
    }

    Import-EitasActiveDirectoryModule |
        Out-Null

    Get-ADOrganizationalUnit `
        -Identity $TargetOuDn `
        -ErrorAction Stop |
        Out-Null

    $EscapedSam = $SamAccountName.Replace(
        "'",
        "''"
    )

    $ExistingUser = Get-ADUser `
        -Filter "SamAccountName -eq '$EscapedSam'" `
        -ErrorAction SilentlyContinue

    if ($ExistingUser) {
        throw "Utilisateur déjà existant : $SamAccountName"
    }

    $SecurePassword = ConvertTo-SecureString `
        -String ([string]$TemporaryPassword) `
        -AsPlainText `
        -Force

    $NewUserParams = @{
        Name = $Name
        GivenName = $FirstName
        Surname = $LastName
        DisplayName = $DisplayName
        SamAccountName = $SamAccountName
        UserPrincipalName = $UserPrincipalName
        Path = $TargetOuDn
        AccountPassword = $SecurePassword
        Enabled = $Enabled
        ChangePasswordAtLogon = $ForceChangeAtLogon
        ErrorAction = "Stop"
    }

    if (
        -not [string]::IsNullOrWhiteSpace(
            [string]$Description
        )
    ) {
        $NewUserParams.Description = $Description
    }

    New-ADUser @NewUserParams

    if ($ForceChangeAtLogon) {
        Set-ADUser `
            -Identity $SamAccountName `
            -ChangePasswordAtLogon $true `
            -ErrorAction Stop
    }

    $CreatedUser = Get-ADUser `
        -Identity $SamAccountName `
        -Properties `
            objectClass, `
            sAMAccountName, `
            userPrincipalName, `
            displayName, `
            description, `
            mail, `
            title, `
            department, `
            company, `
            telephoneNumber, `
            physicalDeliveryOfficeName, `
            Enabled `
        -ErrorAction Stop

    return [pscustomobject]@{
        action = "create_user"
        simulated = $false
        user = $CreatedUser.Name
        display_name = $CreatedUser.DisplayName
        sam_account_name = $CreatedUser.SamAccountName
        user_principal_name = $CreatedUser.UserPrincipalName
        distinguished_name = $CreatedUser.DistinguishedName
        target_ou_dn = $TargetOuDn
        enabled = $CreatedUser.Enabled
        force_change_at_logon = $ForceChangeAtLogon
        created_user = Convert-EitasAdAdminObjectItem `
            -Object $CreatedUser
        message = "Utilisateur AD créé"
    }
}


# BLOC294A - AD computer management

function Invoke-EitasAdAdminCreateComputer {
    param(
        [object]$Config,
        [object]$Payload,
        [string]$Mode
    )

    $Name = Get-EitasObjectValue `
        -Object $Payload `
        -Names @(
            "name",
            "computer_name",
            "computerName"
        )

    $SuppliedSamAccountName = Get-EitasObjectValue `
        -Object $Payload `
        -Names @(
            "sam_account_name",
            "samAccountName",
            "sAMAccountName"
        )

    $TargetOuDn = Get-EitasObjectValue `
        -Object $Payload `
        -Names @(
            "target_ou_dn",
            "targetOuDn",
            "parent_dn",
            "parentDn",
            "path"
        )

    $Description = Get-EitasObjectValue `
        -Object $Payload `
        -Names @(
            "description",
            "comment"
        )

    $Location = Get-EitasObjectValue `
        -Object $Payload `
        -Names @(
            "location",
            "office",
            "site"
        )

    $EnabledValue = Get-EitasObjectValue `
        -Object $Payload `
        -Names @(
            "enabled",
            "active"
        )

    if ([string]::IsNullOrWhiteSpace([string]$Name)) {
        throw "Nom ordinateur manquant"
    }

    if ([string]::IsNullOrWhiteSpace([string]$TargetOuDn)) {
        throw "OU cible ordinateur manquante"
    }

    $Name = ([string]$Name).Trim().ToUpperInvariant()
    $TargetOuDn = ([string]$TargetOuDn).Trim()
    $DescriptionText = [string]$Description
    $LocationText = [string]$Location

    if (
        $Name.Length -gt 15 -or
        $Name -notmatch "^[A-Z0-9-]+$"
    ) {
        throw "Le nom ordinateur doit contenir 1 à 15 caractères : lettres, chiffres et tirets"
    }

    if (
        $Name.StartsWith("-") -or
        $Name.EndsWith("-")
    ) {
        throw "Le nom ordinateur ne peut pas commencer ou finir par un tiret"
    }

    if ($Name -match "^[0-9]+$") {
        throw "Le nom ordinateur ne peut pas contenir uniquement des chiffres"
    }

    if ($DescriptionText.Length -gt 1024) {
        throw "La description ordinateur est limitée à 1024 caractères"
    }

    if ($LocationText.Length -gt 128) {
        throw "L’emplacement ordinateur est limité à 128 caractères"
    }

    $ComputerSamAccountName = $Name + '$'

    if (
        -not [string]::IsNullOrWhiteSpace(
            [string]$SuppliedSamAccountName
        )
    ) {
        $NormalizedSuppliedSam = (
            [string]$SuppliedSamAccountName
        ).Trim().ToUpperInvariant()

        if (-not $NormalizedSuppliedSam.EndsWith('$')) {
            $NormalizedSuppliedSam = (
                $NormalizedSuppliedSam + '$'
            )
        }

        if (
            $NormalizedSuppliedSam -ine
            $ComputerSamAccountName
        ) {
            throw "L’identifiant ordinateur ne correspond pas au nom demandé"
        }
    }

    $DnParts = @(
        $TargetOuDn -split "," |
            ForEach-Object {
                $_.Trim().ToUpperInvariant()
            }
    )

    $IsComputerOu = $false

    if (
        $DnParts.Count -gt 0 -and
        $DnParts[0].StartsWith("OU=")
    ) {
        for (
            $Index = 0;
            $Index -lt ($DnParts.Count - 1);
            $Index++
        ) {
            if (
                $DnParts[$Index] -eq "OU=COMPUTERS" -and
                $DnParts[$Index + 1] -eq "OU=EITAS"
            ) {
                $IsComputerOu = $true
                break
            }
        }
    }

    if (-not $IsComputerOu) {
        throw "La destination ordinateur doit appartenir à OU=Computers,OU=EITAS"
    }

    Assert-EitasDnSafe `
        -DistinguishedName $TargetOuDn `
        -Config $Config |
        Out-Null

    $Enabled = Convert-EitasAdAdminBool `
        -Value $EnabledValue `
        -Default $false

    if ($Mode -ne "Production") {
        return [pscustomobject]@{
            action = "create_computer"
            simulated = $true
            name = $Name
            sam_account_name = $ComputerSamAccountName
            target_ou_dn = $TargetOuDn
            description = $DescriptionText
            location = $LocationText
            enabled = $Enabled
            message = "Simulation création ordinateur AD"
        }
    }

    Import-EitasActiveDirectoryModule |
        Out-Null

    Get-ADOrganizationalUnit `
        -Identity $TargetOuDn `
        -ErrorAction Stop |
        Out-Null

    $EscapedName = Escape-EitasLdapFilterValue `
        -Value $Name

    $EscapedSamAccountName = Escape-EitasLdapFilterValue `
        -Value $ComputerSamAccountName

    $LdapFilter = "(|(sAMAccountName={0})(name={1}))" -f $EscapedSamAccountName, $EscapedName

    $LookupParams = @{
        LDAPFilter = $LdapFilter
        Properties = @(
            "sAMAccountName",
            "DistinguishedName"
        )
        ErrorAction = "Stop"
    }

    $ExistingComputer = @(
        Get-ADComputer @LookupParams
    ) | Select-Object -First 1

    if ($null -ne $ExistingComputer) {
        throw "Ordinateur déjà existant : $Name ($($ExistingComputer.DistinguishedName))"
    }

    $CreateParams = @{
        Name = $Name
        SamAccountName = $ComputerSamAccountName
        Path = $TargetOuDn
        Enabled = $Enabled
        ErrorAction = "Stop"
    }

    if (
        -not [string]::IsNullOrWhiteSpace(
            $DescriptionText
        )
    ) {
        $CreateParams.Description = (
            Repair-EitasTextEncoding `
                -Value $DescriptionText
        )
    }

    if (
        -not [string]::IsNullOrWhiteSpace(
            $LocationText
        )
    ) {
        $CreateParams.Location = (
            Repair-EitasTextEncoding `
                -Value $LocationText
        )
    }

    New-ADComputer @CreateParams

    $ReadParams = @{
        Identity = $ComputerSamAccountName
        Properties = @(
            "Enabled",
            "Description",
            "Location",
            "DNSHostName",
            "OperatingSystem",
            "OperatingSystemVersion",
            "PasswordLastSet",
            "whenCreated",
            "whenChanged"
        )
        ErrorAction = "Stop"
    }

    $CreatedComputer = Get-ADComputer @ReadParams

    return [pscustomobject]@{
        action = "create_computer"
        simulated = $false
        name = $CreatedComputer.Name
        sam_account_name = $CreatedComputer.SamAccountName
        distinguished_name = $CreatedComputer.DistinguishedName
        target_ou_dn = $TargetOuDn
        enabled = $CreatedComputer.Enabled
        description = $CreatedComputer.Description
        location = $CreatedComputer.Location
        dns_host_name = $CreatedComputer.DNSHostName
        created_computer = (
            Convert-EitasAdAdminObjectItem `
                -Object $CreatedComputer
        )
        message = "Ordinateur Active Directory créé"
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
        "location",
        "displayName",
        "givenName",
        "sn",
        "mail",
        "title",
        "department",
        "division",
        "company",
        "telephoneNumber",
        "mobile",
        "physicalDeliveryOfficeName",
        "employeeID",
        "employeeNumber",
        "manager",
        "groupScope",
        "groupCategory",
        "managedBy",
        "protectedFromAccidentalDeletion",
        "streetAddress",
        "postalCode",
        "l",
        "st",
        "co"
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

    $UserOnlyProperties = @(
        "givenName",
        "sn"
    )

    $HasUserOnlyChanges = @(
        $Properties.Keys |
            Where-Object {
                $UserOnlyProperties -contains [string]$_
            }
    ).Count -gt 0

    if (
        $HasUserOnlyChanges -and
        [string]$Object.ObjectClass -ne "user"
    ) {
        throw "givenName et sn sont réservés aux objets utilisateur"
    }

    $Replace = @{}
    $Clear = @()

    $GroupScope = $null
    $GroupCategory = $null
    $ManagedBy = $null
    $ClearManagedBy = $false
    $ProtectedFromAccidentalDeletion = $null

    foreach ($Key in $Properties.Keys) {
        $RawValue = $Properties[$Key]

        if ($Key -eq "protectedFromAccidentalDeletion") {
            if ($RawValue -isnot [bool]) {
                throw "protectedFromAccidentalDeletion doit être un booléen"
            }

            $ProtectedFromAccidentalDeletion = [bool]$RawValue
            continue
        }

        $Value = Repair-EitasTextEncoding -Value $RawValue

        if ($Key -eq "groupScope") {
            $GroupScope = [string]$Value

            if (@("Global", "Universal", "DomainLocal") -notcontains $GroupScope) {
                throw "groupScope doit être Global, Universal ou DomainLocal"
            }
        } elseif ($Key -eq "groupCategory") {
            $GroupCategory = [string]$Value

            if (@("Security", "Distribution") -notcontains $GroupCategory) {
                throw "groupCategory doit être Security ou Distribution"
            }
        } elseif ($Key -eq "managedBy") {
            if (
                $null -eq $Value -or
                [string]::IsNullOrWhiteSpace([string]$Value)
            ) {
                $ClearManagedBy = $true
            } else {
                $ManagedBy = [string]$Value
            }
        } elseif (
            $null -eq $Value -or
            [string]::IsNullOrWhiteSpace([string]$Value)
        ) {
            $Clear += $Key
        } else {
            $Replace[$Key] = [string]$Value
        }
    }

    $ObjectClassName = (
        [string]$Object.ObjectClass
    ).Trim().ToLowerInvariant()

    $HasGroupSpecificChanges = (
        $null -ne $GroupScope -or
        $null -ne $GroupCategory
    )

    if (
        $HasGroupSpecificChanges -and
        $ObjectClassName -ne "group"
    ) {
        throw "groupScope et groupCategory sont réservés aux objets groupe"
    }

    $HasManagedByChanges = (
        $null -ne $ManagedBy -or
        $ClearManagedBy
    )

    if (
        $HasManagedByChanges -and
        @(
            "group",
            "computer",
            "organizationalunit"
        ) -notcontains $ObjectClassName
    ) {
        throw "managedBy est réservé aux groupes, ordinateurs et unités d'organisation"
    }

    if (
        $null -ne $ProtectedFromAccidentalDeletion -and
        $ObjectClassName -ne "organizationalunit"
    ) {
        throw "La protection contre la suppression accidentelle est réservée aux unités d'organisation"
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

    if (
        $HasGroupSpecificChanges -or
        (
            $HasManagedByChanges -and
            $ObjectClassName -eq "group"
        )
    ) {
        $SetGroupParameters = @{
            Identity = $ObjectDn
            ErrorAction = "Stop"
        }

        if ($null -ne $GroupScope) {
            $SetGroupParameters["GroupScope"] = $GroupScope
        }

        if ($null -ne $GroupCategory) {
            $SetGroupParameters["GroupCategory"] = $GroupCategory
        }

        if ($null -ne $ManagedBy) {
            $SetGroupParameters["ManagedBy"] = $ManagedBy
        }

        if ($SetGroupParameters.Count -gt 2) {
            Set-ADGroup @SetGroupParameters
        }

        if ($ClearManagedBy) {
            Set-ADGroup `
                -Identity $ObjectDn `
                -Clear "managedBy" `
                -ErrorAction Stop
        }
    }

    if (
        $HasManagedByChanges -and
        $ObjectClassName -eq "computer"
    ) {
        if ($null -ne $ManagedBy) {
            Set-ADComputer `
                -Identity $ObjectDn `
                -ManagedBy $ManagedBy `
                -ErrorAction Stop
        }

        if ($ClearManagedBy) {
            Set-ADComputer `
                -Identity $ObjectDn `
                -Clear "managedBy" `
                -ErrorAction Stop
        }
    }

    if (
        $HasManagedByChanges -and
        $ObjectClassName -eq "organizationalunit"
    ) {
        if ($null -ne $ManagedBy) {
            Set-ADOrganizationalUnit `
                -Identity $ObjectDn `
                -ManagedBy $ManagedBy `
                -ErrorAction Stop
        }

        if ($ClearManagedBy) {
            Set-ADOrganizationalUnit `
                -Identity $ObjectDn `
                -Clear "managedBy" `
                -ErrorAction Stop
        }
    }

    if ($null -ne $ProtectedFromAccidentalDeletion) {
        Set-ADOrganizationalUnit `
            -Identity $ObjectDn `
            -ProtectedFromAccidentalDeletion $ProtectedFromAccidentalDeletion `
            -ErrorAction Stop
    }


    $UpdatedObject = Get-ADObject `
        -Identity $ObjectDn `
        -Properties objectClass, sAMAccountName, userPrincipalName, displayName, givenName, sn, description, location, mail, title, department, division, company, telephoneNumber, mobile, physicalDeliveryOfficeName, employeeID, employeeNumber, manager, managedBy, streetAddress, postalCode, l, st, co `
        -ErrorAction Stop

    $UpdatedGroupScope = $null
    $UpdatedGroupCategory = $null
    $UpdatedManagedBy = [string]$UpdatedObject.managedBy
    $UpdatedProtectedFromAccidentalDeletion = $null

    if ([string]$Object.ObjectClass -eq "group") {
        $UpdatedGroup = Get-ADGroup `
            -Identity $ObjectDn `
            -Properties ManagedBy `
            -ErrorAction Stop

        $UpdatedGroupScope = [string]$UpdatedGroup.GroupScope
        $UpdatedGroupCategory = [string]$UpdatedGroup.GroupCategory
    }

    if ($ObjectClassName -eq "organizationalunit") {
        $UpdatedOu = Get-ADOrganizationalUnit `
            -Identity $ObjectDn `
            -Properties ProtectedFromAccidentalDeletion `
            -ErrorAction Stop

        $UpdatedProtectedFromAccidentalDeletion = `
            [bool]$UpdatedOu.ProtectedFromAccidentalDeletion
    }

    return [pscustomobject]@{
        action = "update_object_properties"
        simulated = $false
        object = $Object.Name
        object_type = $Object.ObjectClass
        object_dn = $ObjectDn
        replaced = $Replace
        cleared = $Clear
        group_scope = $UpdatedGroupScope
        group_category = $UpdatedGroupCategory
        managed_by = $UpdatedManagedBy
        protected_from_accidental_deletion = $UpdatedProtectedFromAccidentalDeletion
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
    $IsOu = ([string]$Object.ObjectClass -ieq "organizationalUnit")
    $OuEmptyVerified = $false
    $OuProtectionDisabled = $false

    if ($IsOu) {
        $Children = @(
            Get-ADObject `
                -SearchBase $ObjectDn `
                -SearchScope OneLevel `
                -Filter * `
                -ResultSetSize 1 `
                -ErrorAction Stop
        )

        if ($Children.Count -gt 0) {
            throw "Suppression OU refusée : l'OU contient encore $($Children.Count) objet(s) enfant(s)"
        }

        $OuEmptyVerified = $true

        $Ou = Get-ADOrganizationalUnit `
            -Identity $ObjectDn `
            -Properties ProtectedFromAccidentalDeletion `
            -ErrorAction Stop

        if ([bool]$Ou.ProtectedFromAccidentalDeletion) {
            Set-ADOrganizationalUnit `
                -Identity $ObjectDn `
                -ProtectedFromAccidentalDeletion $false `
                -ErrorAction Stop

            $OuProtectionDisabled = $true
        }
    }

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
        ou_empty_verified = $OuEmptyVerified
        ou_protection_disabled = $OuProtectionDisabled
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
    $ObjectClass = ([string]$Object.ObjectClass).Trim().ToLowerInvariant()
    $IsComputer = $ObjectClass -eq "computer"

    $OldSamAccountName = $null
    $NewSamAccountName = $null

    if ($IsComputer) {
        $NewName = $NewName.ToUpperInvariant()

        if (
            $NewName.Length -lt 1 `
            -or $NewName.Length -gt 15 `
            -or $NewName -notmatch '^[A-Z0-9-]+$'
        ) {
            throw "Nom ordinateur invalide : 1 à 15 caractères, lettres A-Z, chiffres et tirets uniquement"
        }

        $ComputerBefore = Get-ADComputer `
            -Identity $ObjectDn `
            -Properties sAMAccountName `
            -ErrorAction Stop

        $OldSamAccountName = [string]$ComputerBefore.SamAccountName
        $NewSamAccountName = "$NewName`$"

        $ComputerConflict = Get-ADComputer `
            -LDAPFilter "(sAMAccountName=$NewSamAccountName)" `
            -Properties distinguishedName `
            -ErrorAction Stop |
            Where-Object {
                [string]$_.DistinguishedName -ine $ObjectDn
            } |
            Select-Object -First 1

        if ($null -ne $ComputerConflict) {
            throw "Un compte ordinateur utilise déjà l’identifiant $NewSamAccountName"
        }
    }

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
        $SamAccountNameUpdated = $false

        if (
            $IsComputer `
            -and $OldSamAccountName -ine $NewSamAccountName
        ) {
            Set-ADComputer `
                -Identity $ObjectDn `
                -SamAccountName $NewSamAccountName `
                -ErrorAction Stop

            $SamAccountNameUpdated = $true
        }

        $CurrentObject = Get-ADObject `
            -Identity $ObjectDn `
            -Properties objectClass, sAMAccountName, userPrincipalName, displayName, description `
            -ErrorAction Stop

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
            old_sam_account_name = $OldSamAccountName
            new_sam_account_name = [string]$CurrentObject.sAMAccountName
            sam_account_name_updated = $SamAccountNameUpdated
            renamed_object = Convert-EitasAdAdminObjectItem -Object $CurrentObject
            message = $(if ($SamAccountNameUpdated) {
                "Nom déjà correct ; identifiant du compte ordinateur synchronisé"
            } else {
                "L’objet porte déjà ce nom"
            })
        }
    }

    Rename-ADObject `
        -Identity $ObjectDn `
        -NewName $NewName `
        -ErrorAction Stop

    if (
        $IsComputer `
        -and $OldSamAccountName -ine $NewSamAccountName
    ) {
        try {
            Set-ADComputer `
                -Identity $NewDn `
                -SamAccountName $NewSamAccountName `
                -ErrorAction Stop
        }
        catch {
            $SamUpdateError = $_.Exception.Message
            $RollbackError = $null

            try {
                Rename-ADObject `
                    -Identity $NewDn `
                    -NewName $CurrentName `
                    -ErrorAction Stop
            }
            catch {
                $RollbackError = $_.Exception.Message
            }

            if ($RollbackError) {
                throw "Échec de synchronisation du compte ordinateur : $SamUpdateError. Le retour arrière du CN a également échoué : $RollbackError"
            }

            throw "Échec de synchronisation du compte ordinateur : $SamUpdateError. Le renommage du CN a été annulé."
        }
    }

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
        old_sam_account_name = $OldSamAccountName
        new_sam_account_name = [string]$RenamedObject.sAMAccountName
        sam_account_name_updated = $(
            $IsComputer `
            -and $OldSamAccountName -ine [string]$RenamedObject.sAMAccountName
        )
        renamed_object = Convert-EitasAdAdminObjectItem -Object $RenamedObject
        message = $(if ($IsComputer) {
            "Compte ordinateur AD renommé et identifiant synchronisé"
        } else {
            "Objet AD renommé"
        })
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


function Convert-EitasAdAdminBool {
    param(
        [object]$Value,
        [bool]$Default = $false
    )

    if ($null -eq $Value) {
        return $Default
    }

    if ($Value -is [bool]) {
        return [bool]$Value
    }

    $Text = ([string]$Value).Trim().ToLowerInvariant()

    if (@("1", "true", "yes", "oui", "enabled", "active") -contains $Text) {
        return $true
    }

    if (@("0", "false", "no", "non", "disabled", "inactive") -contains $Text) {
        return $false
    }

    return $Default
}

function Get-EitasAdAdminAccountIdentity {
    param([object]$Payload)

    $Identity = Get-EitasObjectValue -Object $Payload -Names @(
        "object_dn",
        "distinguished_name",
        "dn",
        "identity",
        "sam_account_name",
        "samAccountName"
    )

    if ([string]::IsNullOrWhiteSpace([string]$Identity)) {
        throw "Identité compte AD manquante"
    }

    return ([string]$Identity).Trim()
}

function Assert-EitasAdAdminAccountDnAllowed {
    param(
        [object]$Config,
        [string]$ObjectDn
    )

    if ([string]::IsNullOrWhiteSpace($ObjectDn)) {
        throw "DN compte AD manquant"
    }

    $AllowedBaseDn = Get-EitasObjectValue -Object $Config -Names @(
        "EitasBaseOu",
        "AllowedBaseDn",
        "BaseDn",
        "DomainBaseDn"
    )

    if (-not [string]::IsNullOrWhiteSpace([string]$AllowedBaseDn)) {
        $CleanDn = $ObjectDn.Trim().ToLowerInvariant()
        $CleanBase = ([string]$AllowedBaseDn).Trim().ToLowerInvariant()

        if (-not $CleanDn.EndsWith($CleanBase)) {
            throw "DN hors périmètre EITAS : $ObjectDn"
        }
    }
}

function Resolve-EitasAdAdminEnableDisableAccount {
    param(
        [object]$Config,
        [string]$Identity
    )

    Import-Module ActiveDirectory -ErrorAction Stop

    $BaseObject = Get-ADObject `
        -Identity $Identity `
        -Properties objectClass `
        -ErrorAction Stop

    $ObjectDn = [string]$BaseObject.DistinguishedName

    Assert-EitasAdAdminAccountDnAllowed `
        -Config $Config `
        -ObjectDn $ObjectDn

    $ObjectClass = (
        [string]$BaseObject.ObjectClass
    ).Trim().ToLowerInvariant()

    if ($ObjectClass -eq "user") {
        return Get-ADUser `
            -Identity $ObjectDn `
            -Properties `
                Enabled, `
                LockedOut, `
                PasswordExpired, `
                PasswordLastSet, `
                UserPrincipalName, `
                SamAccountName, `
                DisplayName, `
                Description, `
                objectClass `
            -ErrorAction Stop
    }

    if ($ObjectClass -eq "computer") {
        return Get-ADComputer `
            -Identity $ObjectDn `
            -Properties `
                Enabled, `
                PasswordLastSet, `
                SamAccountName, `
                Description, `
                Location, `
                DNSHostName, `
                OperatingSystem, `
                OperatingSystemVersion, `
                objectClass `
            -ErrorAction Stop
    }

    throw "Type de compte incompatible avec Activer/Désactiver : $ObjectClass"
}


function Resolve-EitasAdAdminAccountUser {
    param(
        [object]$Config,
        [string]$Identity
    )

    Import-Module ActiveDirectory -ErrorAction Stop

    $User = Get-ADUser `
        -Identity $Identity `
        -Properties Enabled, LockedOut, PasswordExpired, PasswordLastSet, UserPrincipalName, SamAccountName, DisplayName, Description `
        -ErrorAction Stop

    Assert-EitasAdAdminAccountDnAllowed -Config $Config -ObjectDn $User.DistinguishedName

    return $User
}

function Convert-EitasAdAdminAccountResult {
    param(
        [string]$Action,
        [bool]$Simulated,
        [object]$User,
        [string]$ObjectDn,
        [string]$Message
    )

    $Result = [ordered]@{
        action = $Action
        simulated = $Simulated
        object_dn = $ObjectDn
        message = $Message
    }

    if ($null -ne $User) {
        $Result.object = Get-EitasObjectValue `
            -Object $User `
            -Names @("Name", "name")

        $Result.user = $Result.object

        $Result.object_type = Get-EitasObjectValue `
            -Object $User `
            -Names @("ObjectClass", "objectClass")

        $Result.sam_account_name = Get-EitasObjectValue `
            -Object $User `
            -Names @("SamAccountName", "sAMAccountName")

        $Result.user_principal_name = Get-EitasObjectValue `
            -Object $User `
            -Names @("UserPrincipalName")

        $Result.enabled = Get-EitasObjectValue `
            -Object $User `
            -Names @("Enabled")

        $Result.locked_out = Get-EitasObjectValue `
            -Object $User `
            -Names @("LockedOut")

        $Result.password_expired = Get-EitasObjectValue `
            -Object $User `
            -Names @("PasswordExpired")

        $Result.password_last_set = Get-EitasObjectValue `
            -Object $User `
            -Names @("PasswordLastSet")

        $Result.distinguished_name = Get-EitasObjectValue `
            -Object $User `
            -Names @("DistinguishedName")

        if (
            Get-Command `
                Convert-EitasAdAdminObjectItem `
                -ErrorAction SilentlyContinue
        ) {
            $Result.updated_object =
                Convert-EitasAdAdminObjectItem `
                    -Object $User
        }
    }

    return [pscustomobject]$Result
}

function Invoke-EitasAdAdminEnableAccount {
    param(
        [object]$Config,
        [object]$Payload,
        [string]$Mode
    )

    $Identity = Get-EitasAdAdminAccountIdentity -Payload $Payload

    if ($Mode -ne "Production") {
        return Convert-EitasAdAdminAccountResult `
            -Action "enable_account" `
            -Simulated $true `
            -User $null `
            -ObjectDn $Identity `
            -Message "Simulation activation compte AD"
    }

    $User = Resolve-EitasAdAdminEnableDisableAccount -Config $Config -Identity $Identity
    Enable-ADAccount -Identity $User.DistinguishedName -ErrorAction Stop

    $UpdatedUser = Resolve-EitasAdAdminEnableDisableAccount -Config $Config -Identity $User.DistinguishedName

    return Convert-EitasAdAdminAccountResult `
        -Action "enable_account" `
        -Simulated $false `
        -User $UpdatedUser `
        -ObjectDn $UpdatedUser.DistinguishedName `
        -Message "Compte AD activé"
}

function Invoke-EitasAdAdminDisableAccount {
    param(
        [object]$Config,
        [object]$Payload,
        [string]$Mode
    )

    $Identity = Get-EitasAdAdminAccountIdentity -Payload $Payload

    if ($Mode -ne "Production") {
        return Convert-EitasAdAdminAccountResult `
            -Action "disable_account" `
            -Simulated $true `
            -User $null `
            -ObjectDn $Identity `
            -Message "Simulation désactivation compte AD"
    }

    $User = Resolve-EitasAdAdminEnableDisableAccount -Config $Config -Identity $Identity
    Disable-ADAccount -Identity $User.DistinguishedName -ErrorAction Stop

    $UpdatedUser = Resolve-EitasAdAdminEnableDisableAccount -Config $Config -Identity $User.DistinguishedName

    return Convert-EitasAdAdminAccountResult `
        -Action "disable_account" `
        -Simulated $false `
        -User $UpdatedUser `
        -ObjectDn $UpdatedUser.DistinguishedName `
        -Message "Compte AD désactivé"
}

function Invoke-EitasAdAdminUnlockAccount {
    param(
        [object]$Config,
        [object]$Payload,
        [string]$Mode
    )

    $Identity = Get-EitasAdAdminAccountIdentity -Payload $Payload

    if ($Mode -ne "Production") {
        return Convert-EitasAdAdminAccountResult `
            -Action "unlock_account" `
            -Simulated $true `
            -User $null `
            -ObjectDn $Identity `
            -Message "Simulation déverrouillage compte AD"
    }

    $User = Resolve-EitasAdAdminAccountUser -Config $Config -Identity $Identity
    Unlock-ADAccount -Identity $User.DistinguishedName -ErrorAction Stop

    $UpdatedUser = Resolve-EitasAdAdminAccountUser -Config $Config -Identity $User.DistinguishedName

    return Convert-EitasAdAdminAccountResult `
        -Action "unlock_account" `
        -Simulated $false `
        -User $UpdatedUser `
        -ObjectDn $UpdatedUser.DistinguishedName `
        -Message "Compte AD déverrouillé"
}

function Invoke-EitasAdAdminResetPassword {
    param(
        [object]$Config,
        [object]$Payload,
        [string]$Mode
    )

    $Identity = Get-EitasAdAdminAccountIdentity -Payload $Payload
    $TemporaryPassword = Get-EitasObjectValue -Object $Payload -Names @(
        "temporary_password",
        "password",
        "new_password"
    )

    if ([string]::IsNullOrWhiteSpace([string]$TemporaryPassword)) {
        throw "Mot de passe temporaire manquant"
    }

    $ForceChangeAtLogon = Convert-EitasAdAdminBool `
        -Value (Get-EitasObjectValue -Object $Payload -Names @("force_change_at_logon", "change_password_at_logon")) `
        -Default $true

    $UnlockAfterReset = Convert-EitasAdAdminBool `
        -Value (Get-EitasObjectValue -Object $Payload -Names @("unlock_after_reset")) `
        -Default $true

    if ($Mode -ne "Production") {
        return [pscustomobject]@{
            action = "reset_password"
            simulated = $true
            object_dn = $Identity
            force_change_at_logon = $ForceChangeAtLogon
            unlock_after_reset = $UnlockAfterReset
            message = "Simulation réinitialisation mot de passe AD"
        }
    }

    $User = Resolve-EitasAdAdminAccountUser -Config $Config -Identity $Identity

    $SecurePassword = ConvertTo-SecureString `
        -String ([string]$TemporaryPassword) `
        -AsPlainText `
        -Force

    Set-ADAccountPassword `
        -Identity $User.DistinguishedName `
        -Reset `
        -NewPassword $SecurePassword `
        -ErrorAction Stop

    if ($ForceChangeAtLogon) {
        Set-ADUser `
            -Identity $User.DistinguishedName `
            -ChangePasswordAtLogon $true `
            -ErrorAction Stop
    }

    if ($UnlockAfterReset) {
        Unlock-ADAccount `
            -Identity $User.DistinguishedName `
            -ErrorAction Stop
    }

    $UpdatedUser = Resolve-EitasAdAdminAccountUser -Config $Config -Identity $User.DistinguishedName

    $Result = Convert-EitasAdAdminAccountResult `
        -Action "reset_password" `
        -Simulated $false `
        -User $UpdatedUser `
        -ObjectDn $UpdatedUser.DistinguishedName `
        -Message "Mot de passe AD réinitialisé"

    $Result | Add-Member -NotePropertyName force_change_at_logon -NotePropertyValue $ForceChangeAtLogon -Force
    $Result | Add-Member -NotePropertyName unlock_after_reset -NotePropertyValue $UnlockAfterReset -Force

    return $Result
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

        
        "create_computer" {
            return Invoke-EitasAdAdminCreateComputer -Config $Config -Payload $Payload -Mode $Mode
        }

        "create_user" {
            return Invoke-EitasAdAdminCreateUser -Config $Config -Payload $Payload -Mode $Mode
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

        "enable_account" {
            return Invoke-EitasAdAdminEnableAccount -Config $Config -Payload $Payload -Mode $Mode
        }

        "disable_account" {
            return Invoke-EitasAdAdminDisableAccount -Config $Config -Payload $Payload -Mode $Mode
        }

        "unlock_account" {
            return Invoke-EitasAdAdminUnlockAccount -Config $Config -Payload $Payload -Mode $Mode
        }

        "reset_password" {
            return Invoke-EitasAdAdminResetPassword -Config $Config -Payload $Payload -Mode $Mode
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

