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

    Import-EitasActiveDirectoryModule | Out-Null

    $ParentObject = Get-ADObject `
        -Identity $ParentDn `
        -Properties objectClass, distinguishedName, name `
        -ErrorAction Stop

    Assert-EitasDnSafe `
        -DistinguishedName $ParentObject.DistinguishedName `
        -Config $Config |
        Out-Null

    $ParentObjectClass = ([string]$ParentObject.ObjectClass).Trim()

    if (
        $ParentObjectClass -ine "organizationalUnit" `
        -and $ParentObjectClass -ine "container"
    ) {
        throw "Parent invalide : la création d'une OU nécessite une OU ou un conteneur AD"
    }

    if (
        Test-EitasAdObjectExists `
            -Identity $Name `
            -SearchBase $ParentDn `
            -ObjectClass "organizationalUnit"
    ) {
        throw "OU déjà existante : $Name dans $ParentDn"
    }

    if ($Mode -ne "Production") {
        return [pscustomobject]@{
            action = "create_ou"
            simulated = $true
            name = $Name
            parent_dn = $ParentDn
            message = "Simulation création OU"
        }
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

function Invoke-EitasAdAdminCreateContact {
    param(
        [object]$Config,
        [object]$Payload,
        [string]$Mode
    )

    $Name = Get-EitasObjectValue -Object $Payload -Names @(
        "name",
        "contact_name",
        "contactName"
    )

    $TargetParentDn = Get-EitasObjectValue -Object $Payload -Names @(
        "target_parent_dn",
        "targetParentDn",
        "parent_dn",
        "parentDn"
    )

    $DisplayName = Get-EitasObjectValue -Object $Payload -Names @(
        "display_name",
        "displayName"
    )

    $FirstName = Get-EitasObjectValue -Object $Payload -Names @(
        "first_name",
        "firstName",
        "given_name",
        "givenName"
    )

    $LastName = Get-EitasObjectValue -Object $Payload -Names @(
        "last_name",
        "lastName",
        "surname",
        "sn"
    )

    $Mail = Get-EitasObjectValue -Object $Payload -Names @(
        "mail",
        "email"
    )

    $TelephoneNumber = Get-EitasObjectValue -Object $Payload -Names @(
        "telephone_number",
        "telephoneNumber",
        "phone"
    )

    $Mobile = Get-EitasObjectValue -Object $Payload -Names @(
        "mobile",
        "mobile_phone"
    )

    $Company = Get-EitasObjectValue -Object $Payload -Names @("company")
    $Title = Get-EitasObjectValue -Object $Payload -Names @("title")
    $Department = Get-EitasObjectValue -Object $Payload -Names @("department")
    $Description = Get-EitasObjectValue -Object $Payload -Names @("description")

    $ProtectedRaw = Get-EitasObjectValue -Object $Payload -Names @(
        "protected_from_accidental_deletion",
        "protectedFromAccidentalDeletion"
    )

    if ([string]::IsNullOrWhiteSpace([string]$Name)) {
        throw "Nom contact manquant"
    }

    $Name = ([string]$Name).Trim()

    if ([string]::IsNullOrWhiteSpace([string]$TargetParentDn)) {
        throw "Parent DN manquant pour création contact"
    }

    $TargetParentDn = ([string]$TargetParentDn).Trim()

    if ([string]::IsNullOrWhiteSpace([string]$DisplayName)) {
        $DisplayName = $Name
    } else {
        $DisplayName = ([string]$DisplayName).Trim()
    }

    $ProtectedFromAccidentalDeletion = $true

    if ($null -ne $ProtectedRaw) {
        if ($ProtectedRaw -isnot [bool]) {
            throw "protectedFromAccidentalDeletion doit être un booléen"
        }

        $ProtectedFromAccidentalDeletion = [bool]$ProtectedRaw
    }

    Assert-EitasDnSafe `
        -DistinguishedName $TargetParentDn `
        -Config $Config |
        Out-Null

    Import-EitasActiveDirectoryModule | Out-Null

    $ParentObject = Get-ADObject `
        -Identity $TargetParentDn `
        -Properties objectClass, distinguishedName, name `
        -ErrorAction Stop

    Assert-EitasDnSafe `
        -DistinguishedName $ParentObject.DistinguishedName `
        -Config $Config |
        Out-Null

    $ParentObjectClass = (
        [string]$ParentObject.ObjectClass
    ).Trim()

    if (
        $ParentObjectClass -ine "organizationalUnit" `
        -and $ParentObjectClass -ine "container"
    ) {
        throw "Parent invalide : un contact nécessite une OU ou un conteneur AD"
    }

    if (
        Test-EitasAdObjectExists `
            -Identity $Name `
            -SearchBase $TargetParentDn `
            -ObjectClass "contact"
    ) {
        throw "Contact déjà existant : $Name dans $TargetParentDn"
    }

    if ($Mode -ne "Production") {
        return [pscustomobject]@{
            action = "create_contact"
            simulated = $true
            name = $Name
            display_name = $DisplayName
            target_parent_dn = $TargetParentDn
            protected_from_accidental_deletion = (
                $ProtectedFromAccidentalDeletion
            )
            message = "Simulation création contact"
        }
    }

    $OtherAttributes = @{}

    $AttributeMap = @{
        givenName = $FirstName
        sn = $LastName
        mail = $Mail
        telephoneNumber = $TelephoneNumber
        mobile = $Mobile
        company = $Company
        title = $Title
        department = $Department
    }

    foreach ($Key in $AttributeMap.Keys) {
        $Value = [string]$AttributeMap[$Key]

        if (-not [string]::IsNullOrWhiteSpace($Value)) {
            $OtherAttributes[$Key] = (
                Repair-EitasTextEncoding -Value $Value
            )
        }
    }

    $Params = @{
        Name = $Name
        Type = "contact"
        Path = $TargetParentDn
        DisplayName = (
            Repair-EitasTextEncoding -Value $DisplayName
        )
        ProtectedFromAccidentalDeletion = (
            $ProtectedFromAccidentalDeletion
        )
        ErrorAction = "Stop"
    }

    if (
        -not [string]::IsNullOrWhiteSpace(
            [string]$Description
        )
    ) {
        $Params.Description = (
            Repair-EitasTextEncoding -Value $Description
        )
    }

    if ($OtherAttributes.Count -gt 0) {
        $Params.OtherAttributes = $OtherAttributes
    }

    New-ADObject @Params

    $ContactDn = "CN=$Name,$TargetParentDn"

    $CreatedContact = Get-ADObject `
        -Identity $ContactDn `
        -Properties `
            objectClass, `
            displayName, `
            givenName, `
            sn, `
            mail, `
            telephoneNumber, `
            mobile, `
            company, `
            title, `
            department, `
            description, `
            ProtectedFromAccidentalDeletion `
        -ErrorAction Stop

    return [pscustomobject]@{
        action = "create_contact"
        simulated = $false
        name = $CreatedContact.Name
        display_name = [string]$CreatedContact.DisplayName
        distinguished_name = [string]$CreatedContact.DistinguishedName
        target_parent_dn = $TargetParentDn
        protected_from_accidental_deletion = (
            [bool]$CreatedContact.ProtectedFromAccidentalDeletion
        )
        created_contact = Convert-EitasAdAdminObjectItem `
            -Object $CreatedContact
        message = "Contact AD créé"
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

    Import-EitasActiveDirectoryModule | Out-Null

    if (Test-EitasAdObjectExists -Identity $SamAccountName -SearchBase $ParentDn -ObjectClass "group") {
        throw "Groupe déjà existant : $SamAccountName dans $ParentDn"
    }

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

    $CreateUserProfileSpecs = @(
        [pscustomobject]@{
            Key = "title"
            Names = @(
                "title",
                "Title"
            )
            Parameter = "Title"
            MaximumLength = 128
        },
        [pscustomobject]@{
            Key = "department"
            Names = @(
                "department",
                "Department"
            )
            Parameter = "Department"
            MaximumLength = 64
        },
        [pscustomobject]@{
            Key = "division"
            Names = @(
                "division",
                "Division"
            )
            Parameter = "Division"
            MaximumLength = 256
        },
        [pscustomobject]@{
            Key = "company"
            Names = @(
                "company",
                "Company"
            )
            Parameter = "Company"
            MaximumLength = 64
        },
        [pscustomobject]@{
            Key = "manager"
            Names = @(
                "manager",
                "Manager"
            )
            Parameter = "Manager"
            MaximumLength = 2048
        },
        [pscustomobject]@{
            Key = "office"
            Names = @(
                "office",
                "Office",
                "physical_delivery_office_name",
                "physicalDeliveryOfficeName"
            )
            Parameter = "Office"
            MaximumLength = 128
        },
        [pscustomobject]@{
            Key = "telephone_number"
            Names = @(
                "telephone_number",
                "telephoneNumber",
                "office_phone",
                "officePhone",
                "OfficePhone"
            )
            Parameter = "OfficePhone"
            MaximumLength = 64
        },
        [pscustomobject]@{
            Key = "mobile"
            Names = @(
                "mobile",
                "Mobile",
                "mobile_phone",
                "mobilePhone",
                "MobilePhone"
            )
            Parameter = "MobilePhone"
            MaximumLength = 64
        },
        [pscustomobject]@{
            Key = "street_address"
            Names = @(
                "street_address",
                "streetAddress",
                "StreetAddress"
            )
            Parameter = "StreetAddress"
            MaximumLength = 1024
        },
        [pscustomobject]@{
            Key = "postal_code"
            Names = @(
                "postal_code",
                "postalCode",
                "PostalCode"
            )
            Parameter = "PostalCode"
            MaximumLength = 40
        },
        [pscustomobject]@{
            Key = "city"
            Names = @(
                "city",
                "City",
                "l"
            )
            Parameter = "City"
            MaximumLength = 128
        },
        [pscustomobject]@{
            Key = "state"
            Names = @(
                "state",
                "State",
                "st"
            )
            Parameter = "State"
            MaximumLength = 128
        }
    )

    $CreateUserProfileValues = @{}
    $AppliedProfileFields = @()

    foreach ($ProfileSpec in $CreateUserProfileSpecs) {
        $RawProfileValue = Get-EitasObjectValue `
            -Object $Payload `
            -Names $ProfileSpec.Names

        if (
            [string]::IsNullOrWhiteSpace(
                [string]$RawProfileValue
            )
        ) {
            continue
        }

        $ProfileValue = Repair-EitasTextEncoding `
            -Value (
                [string]$RawProfileValue
            ).Trim()

        if (
            $ProfileValue.ToCharArray() |
            Where-Object {
                [int][char]$_ -lt 32
            }
        ) {
            throw (
                "$($ProfileSpec.Key) contient " +
                "un caractère de contrôle interdit"
            )
        }

        if (
            $ProfileValue.Length -gt
            [int]$ProfileSpec.MaximumLength
        ) {
            throw (
                "$($ProfileSpec.Key) est limité à " +
                "$($ProfileSpec.MaximumLength) caractères"
            )
        }

        $CreateUserProfileValues[
            [string]$ProfileSpec.Parameter
        ] = $ProfileValue

        $AppliedProfileFields +=
            [string]$ProfileSpec.Key
    }

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

    if (
        -not [string]::IsNullOrWhiteSpace(
            [string]$Description
        )
    ) {
        $AppliedProfileFields += "description"
    }

    $AppliedProfileFields = @(
        $AppliedProfileFields |
            Sort-Object -Unique
    )

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
            profile_fields = @(
                $AppliedProfileFields
            )
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

    foreach (
        $ProfileParameter
        in $CreateUserProfileValues.Keys
    ) {
        $NewUserParams[
            [string]$ProfileParameter
        ] = $CreateUserProfileValues[
            [string]$ProfileParameter
        ]
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
            division, `
            manager, `
            telephoneNumber, `
            mobile, `
            physicalDeliveryOfficeName, `
            streetAddress, `
            postalCode, `
            l, `
            st, `
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
        profile_fields = @(
            $AppliedProfileFields
        )
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

    $Group = Get-ADGroup -Identity $Identity -Properties Description, GroupScope -ErrorAction Stop
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

function Test-EitasAdAdminGroupContainsGroup {
    param(
        [object]$RootGroup,
        [object]$ExpectedGroup
    )

    if (
        $null -eq $RootGroup -or
        $null -eq $ExpectedGroup
    ) {
        return $false
    }

    $ExpectedDn =
        [string]$ExpectedGroup.DistinguishedName

    $RootDn =
        [string]$RootGroup.DistinguishedName

    if (
        [string]::IsNullOrWhiteSpace($ExpectedDn) -or
        [string]::IsNullOrWhiteSpace($RootDn)
    ) {
        return $false
    }

    $Pending =
        New-Object System.Collections.ArrayList

    $Visited = @{}

    [void]$Pending.Add($RootGroup)

    while ($Pending.Count -gt 0) {
        $LastIndex =
            $Pending.Count - 1

        $Current =
            $Pending[$LastIndex]

        $Pending.RemoveAt($LastIndex)

        $CurrentDn =
            [string]$Current.DistinguishedName

        if (
            [string]::IsNullOrWhiteSpace(
                $CurrentDn
            )
        ) {
            continue
        }

        $CurrentKey =
            $CurrentDn.ToLowerInvariant()

        if (
            $Visited.ContainsKey(
                $CurrentKey
            )
        ) {
            continue
        }

        $Visited[$CurrentKey] = $true

        if (
            $CurrentDn -ieq
            $ExpectedDn
        ) {
            return $true
        }

        $DirectMembers = @(
            Get-ADGroupMember `
                -Identity $CurrentDn `
                -ErrorAction Stop
        )

        foreach (
            $DirectMember in
            $DirectMembers
        ) {
            if (
                [string]$DirectMember.ObjectClass `
                    -ine "group"
            ) {
                continue
            }

            $DirectMemberDn =
                [string]$DirectMember.DistinguishedName

            if (
                [string]::IsNullOrWhiteSpace(
                    $DirectMemberDn
                )
            ) {
                continue
            }

            if (
                $DirectMemberDn -ieq
                $ExpectedDn
            ) {
                return $true
            }

            $DirectMemberKey =
                $DirectMemberDn.ToLowerInvariant()

            if (
                -not $Visited.ContainsKey(
                    $DirectMemberKey
                )
            ) {
                [void]$Pending.Add(
                    $DirectMember
                )
            }
        }
    }

    return $false
}



function Assert-EitasAdAdminGroupScopeCompatibility {
    param(
        [object]$Group,
        [object]$Member
    )

    $MemberObjectClass = (
        [string]$Member.ObjectClass
    ).Trim()

    if ($MemberObjectClass -ine "group") {
        return $null
    }

    $TargetScope = (
        [string]$Group.GroupScope
    ).Trim()

    if (
        [string]::IsNullOrWhiteSpace(
            $TargetScope
        )
    ) {
        throw "Portee du groupe cible introuvable"
    }

    $MemberGroup = Get-ADGroup `
        -Identity $Member.DistinguishedName `
        -Properties GroupScope `
        -ErrorAction Stop

    $MemberScope = (
        [string]$MemberGroup.GroupScope
    ).Trim()

    if (
        [string]::IsNullOrWhiteSpace(
            $MemberScope
        )
    ) {
        throw "Portee du groupe membre introuvable"
    }

    $AllowedScopes = @()

    switch ($TargetScope) {
        "Global" {
            $AllowedScopes = @(
                "Global"
            )
        }

        "Universal" {
            $AllowedScopes = @(
                "Global",
                "Universal"
            )
        }

        "DomainLocal" {
            $AllowedScopes = @(
                "Global",
                "Universal",
                "DomainLocal"
            )
        }

        default {
            throw (
                "Portee du groupe cible non prise en charge : " +
                $TargetScope
            )
        }
    }

    if (
        $AllowedScopes -notcontains
        $MemberScope
    ) {
        throw (
            "Imbrication de groupes incompatible : " +
            "groupe cible $TargetScope, " +
            "groupe membre $MemberScope"
        )
    }

    return [pscustomobject]@{
        target_group_scope = $TargetScope
        member_group_scope = $MemberScope
    }
}


function Assert-EitasAdAdminGroupMembershipAdditionSafe {
    param(
        [object]$Group,
        [object]$Member
    )

    if ($null -eq $Group) {
        throw "Groupe cible introuvable"
    }

    if ($null -eq $Member) {
        throw "Membre introuvable"
    }

    if (
        [string]$Group.DistinguishedName -ieq
        [string]$Member.DistinguishedName
    ) {
        throw "Un groupe ne peut pas etre membre de lui-meme"
    }

    if (
        [string]$Member.ObjectClass -ieq
        "group"
    ) {

    $null =
        Assert-EitasAdAdminGroupScopeCompatibility `
            -Group $Group `
            -Member $Member

$WouldCreateCycle =
            Test-EitasAdAdminGroupContainsGroup `
                -RootGroup $Member `
                -ExpectedGroup $Group

        if ($WouldCreateCycle) {
            throw "Imbrication refusee : cette relation creerait un cycle entre groupes"
        }
    }
}


function Invoke-EitasAdAdminSetPrimaryGroup {
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
        "username",
        "name"
    )

    $GroupIdentity = Get-EitasObjectValue -Object $Payload -Names @(
        "group_identity",
        "groupIdentity",
        "group_dn",
        "groupDn",
        "group_name",
        "groupName",
        "group"
    )

    if ([string]::IsNullOrWhiteSpace($ObjectIdentity)) {
        throw "Identite objet manquante"
    }

    if ([string]::IsNullOrWhiteSpace($GroupIdentity)) {
        throw "Identite groupe manquante"
    }

    if ($Mode -eq "Production") {
        throw "set_primary_group est disponible uniquement en mode Simulation"
    }

    $ResolvedObject = Resolve-EitasAdAdminMember `
        -Config $Config `
        -Identity $ObjectIdentity

    $ObjectClass = [string]$ResolvedObject.ObjectClass

    if ($ObjectClass -eq "user") {
        $Subject = Get-ADUser `
            -Identity $ResolvedObject.DistinguishedName `
            -Properties primaryGroupID `
            -ErrorAction Stop
    }
    elseif ($ObjectClass -eq "computer") {
        $Subject = Get-ADComputer `
            -Identity $ResolvedObject.DistinguishedName `
            -Properties primaryGroupID `
            -ErrorAction Stop
    }
    else {
        throw "Le groupe principal est pris en charge uniquement pour les utilisateurs et ordinateurs"
    }

    Assert-EitasDnSafe `
        -DistinguishedName $Subject.DistinguishedName `
        -Config $Config |
        Out-Null

    $ResolvedGroup = Resolve-EitasAdAdminGroup `
        -Config $Config `
        -Identity $GroupIdentity

    $TargetGroup = Get-ADGroup `
        -Identity $ResolvedGroup.DistinguishedName `
        -Properties GroupScope, GroupCategory `
        -ErrorAction Stop

    Assert-EitasDnSafe `
        -DistinguishedName $TargetGroup.DistinguishedName `
        -Config $Config |
        Out-Null

    if ([string]$TargetGroup.GroupCategory -ne "Security") {
        throw "Le groupe principal cible doit etre un groupe de securite"
    }

    if ($null -eq $Subject.SID -or $null -eq $TargetGroup.SID) {
        throw "SID Active Directory introuvable pour le sujet ou le groupe"
    }

    $SubjectDomainSid = [string]$Subject.SID.AccountDomainSid.Value
    $GroupDomainSid = [string]$TargetGroup.SID.AccountDomainSid.Value

    if (
        [string]::IsNullOrWhiteSpace($SubjectDomainSid) -or
        [string]::IsNullOrWhiteSpace($GroupDomainSid) -or
        $SubjectDomainSid -ine $GroupDomainSid
    ) {
        throw "Le groupe principal cible doit appartenir au meme domaine que le sujet"
    }

    $TargetPrimaryGroupId = 0

    try {
        $TargetPrimaryGroupId = [int64](
            $TargetGroup.SID.Value.Split("-")[-1]
        )
    }
    catch {
        throw "RID du groupe principal cible invalide"
    }

    if ($TargetPrimaryGroupId -le 0) {
        throw "RID du groupe principal cible invalide"
    }

    $CurrentPrimaryGroupId = 0

    try {
        $CurrentPrimaryGroupId = [int64]$Subject.primaryGroupID
    }
    catch {
        throw "primaryGroupID actuel invalide"
    }

    $AlreadyPrimary = (
        $CurrentPrimaryGroupId -eq
        $TargetPrimaryGroupId
    )

    $DirectMember = $false

    if (-not $AlreadyPrimary) {
        $Existing = @(
            Get-ADGroupMember `
                -Identity $TargetGroup.DistinguishedName `
                -ErrorAction Stop |
            Where-Object {
                $_.DistinguishedName -ieq
                $Subject.DistinguishedName
            }
        )

        $DirectMember = $Existing.Count -gt 0

        if (-not $DirectMember) {
            throw "Le sujet doit etre membre direct du groupe cible avant de le definir comme groupe principal"
        }
    }

    $Message = if ($AlreadyPrimary) {
        "Le groupe cible est deja le groupe principal"
    }
    else {
        "Simulation changement de groupe principal validee"
    }

    return [pscustomobject]@{
        action = "set_primary_group"
        simulated = $true
        production_authorized = $false
        already_primary = $AlreadyPrimary
        direct_member = $DirectMember
        subject = $Subject.Name
        subject_dn = $Subject.DistinguishedName
        subject_type = $ObjectClass
        current_primary_group_id = $CurrentPrimaryGroupId
        target_group = $TargetGroup.Name
        target_group_dn = $TargetGroup.DistinguishedName
        target_group_id = $TargetPrimaryGroupId
        target_group_scope = [string]$TargetGroup.GroupScope
        target_group_category = [string]$TargetGroup.GroupCategory
        message = $Message
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
        throw "Identite groupe manquante"
    }

    if ([string]::IsNullOrWhiteSpace($MemberIdentity)) {
        throw "Identite membre manquante"
    }

    $Group = Resolve-EitasAdAdminGroup `
        -Config $Config `
        -Identity $GroupIdentity

    $Member = Resolve-EitasAdAdminMember `
        -Config $Config `
        -Identity $MemberIdentity

    Assert-EitasAdAdminGroupMembershipAdditionSafe `
        -Group $Group `
        -Member $Member

    $Existing = @(
        Get-ADGroupMember `
            -Identity $Group.DistinguishedName `
            -ErrorAction Stop |
            Where-Object {
                $_.DistinguishedName -ieq
                $Member.DistinguishedName
            }
    )

    if ($Existing.Count -gt 0) {
        return [pscustomobject]@{
            action = "add_group_member"
            simulated = ($Mode -ne "Production")
            already_member = $true
            group = $Group.Name
            member = $Member.Name
            group_dn = $Group.DistinguishedName
            member_dn = $Member.DistinguishedName
            member_object = Convert-EitasAdAdminObjectItem `
                -Object $Member
            message = "Le membre est deja dans le groupe"
        }
    }

    if ($Mode -ne "Production") {
        return [pscustomobject]@{
            action = "add_group_member"
            simulated = $true
            already_member = $false
            group = $Group.Name
            member = $Member.Name
            group_dn = $Group.DistinguishedName
            member_dn = $Member.DistinguishedName
            member_object = Convert-EitasAdAdminObjectItem `
                -Object $Member
            message = "Simulation ajout membre groupe validee"
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
        member_object = Convert-EitasAdAdminObjectItem `
            -Object $Member
        message = "Membre ajoute au groupe"
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
        throw "Identite groupe manquante"
    }

    if ([string]::IsNullOrWhiteSpace($MemberIdentity)) {
        throw "Identite membre manquante"
    }

    $Group = Resolve-EitasAdAdminGroup `
        -Config $Config `
        -Identity $GroupIdentity

    $Member = Resolve-EitasAdAdminMember `
        -Config $Config `
        -Identity $MemberIdentity

    $Existing = @(
        Get-ADGroupMember `
            -Identity $Group.DistinguishedName `
            -ErrorAction Stop |
        Where-Object {
            $_.DistinguishedName -ieq
            $Member.DistinguishedName
        }
    )

    $WasMember = $Existing.Count -gt 0

    if ($Mode -ne "Production") {
        $Message = if ($WasMember) {
            "Simulation retrait membre groupe validee"
        }
        else {
            "Simulation retrait membre groupe : membre deja absent"
        }

        return [pscustomobject]@{
            action = "remove_group_member"
            simulated = $true
            was_member = $WasMember
            group = $Group.Name
            member = $Member.Name
            group_dn = $Group.DistinguishedName
            member_dn = $Member.DistinguishedName
            member_object = Convert-EitasAdAdminObjectItem -Object $Member
            message = $Message
        }
    }

    if (-not $WasMember) {
        return [pscustomobject]@{
            action = "remove_group_member"
            simulated = $false
            was_member = $false
            group = $Group.Name
            member = $Member.Name
            group_dn = $Group.DistinguishedName
            member_dn = $Member.DistinguishedName
            message = "Le membre n'etait pas dans le groupe"
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
        message = "Membre retire du groupe"
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
        $SearchBase = (
            Get-EitasAdDomainDn -Config $Config
        ).Trim()
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




function Resolve-EitasAdAdminManagedByUser {
    param(
        [object]$Config,
        [string]$Identity
    )

    if ([string]::IsNullOrWhiteSpace($Identity)) {
        throw "Identité gestionnaire AD manquante"
    }

    $DomainDn = (
        Get-EitasAdDomainDn -Config $Config
    ).Trim()

    $User = Get-ADUser `
        -Identity $Identity `
        -Properties Enabled, displayName, sAMAccountName `
        -ErrorAction Stop

    $UserDn = (
        [string]$User.DistinguishedName
    ).Trim()

    if ([string]::IsNullOrWhiteSpace($UserDn)) {
        throw "DN du gestionnaire Active Directory introuvable"
    }

    $DomainDnLower = $DomainDn.ToLowerInvariant()
    $UserDnLower = $UserDn.ToLowerInvariant()

    if (
        $UserDnLower -ine $DomainDnLower -and
        -not $UserDnLower.EndsWith(
            "," + $DomainDnLower
        )
    ) {
        throw "Gestionnaire Active Directory hors domaine autorisé : $UserDn"
    }

    if (-not [bool]$User.Enabled) {
        throw "Le gestionnaire Active Directory doit être un utilisateur actif"
    }

    return $User
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



function Assert-EitasAdAdminGroupUpdateTransitionSafe {
    param(
        [object]$Config,
        [string]$ObjectIdentity,
        [object]$Properties
    )

    if (
        $null -eq $Properties -or
        (
            -not $Properties.ContainsKey("groupScope") -and
            -not $Properties.ContainsKey("groupCategory")
        )
    ) {
        return $null
    }

    $Object = Resolve-EitasAdAdminObject `
        -Config $Config `
        -Identity $ObjectIdentity

    if (
        ([string]$Object.ObjectClass).Trim().ToLowerInvariant() -ne
        "group"
    ) {
        throw "groupScope et groupCategory sont reserves aux objets groupe"
    }

    $Group = Get-ADGroup `
        -Identity $Object.DistinguishedName `
        -Properties GroupScope, GroupCategory, MemberOf, SID `
        -ErrorAction Stop

    Assert-EitasDnSafe `
        -DistinguishedName $Group.DistinguishedName `
        -Config $Config |
        Out-Null

    $CurrentScope = ([string]$Group.GroupScope).Trim()
    $CurrentCategory = ([string]$Group.GroupCategory).Trim()

    if (
        @("Global", "Universal", "DomainLocal") -notcontains
        $CurrentScope
    ) {
        throw (
            "Portee actuelle du groupe non prise en charge : " +
            $CurrentScope
        )
    }

    if (
        @("Security", "Distribution") -notcontains
        $CurrentCategory
    ) {
        throw (
            "Categorie actuelle du groupe non prise en charge : " +
            $CurrentCategory
        )
    }

    $RequestedScope = $CurrentScope
    $RequestedCategory = $CurrentCategory

    if ($Properties.ContainsKey("groupScope")) {
        $RequestedScope = (
            [string]$Properties["groupScope"]
        ).Trim()
    }

    if ($Properties.ContainsKey("groupCategory")) {
        $RequestedCategory = (
            [string]$Properties["groupCategory"]
        ).Trim()
    }

    if (
        @("Global", "Universal", "DomainLocal") -notcontains
        $RequestedScope
    ) {
        throw "groupScope doit etre Global, Universal ou DomainLocal"
    }

    if (
        @("Security", "Distribution") -notcontains
        $RequestedCategory
    ) {
        throw "groupCategory doit etre Security ou Distribution"
    }

    $DirectScopeConversionForbidden = (
        (
            $CurrentScope -eq "Global" -and
            $RequestedScope -eq "DomainLocal"
        ) -or
        (
            $CurrentScope -eq "DomainLocal" -and
            $RequestedScope -eq "Global"
        )
    )

    if ($DirectScopeConversionForbidden) {
        throw (
            "Conversion directe de portee refusee : " +
            "$CurrentScope vers $RequestedScope. " +
            "Utiliser Universal comme etape intermediaire."
        )
    }

    $ScopeTransition = "$CurrentScope vers $RequestedScope"
    $ParentChecks = @()
    $MemberChecks = @()
    $GroupDomainSid = ""

    if ($null -ne $Group.SID) {
        $GroupDomainSid = [string]$Group.SID.AccountDomainSid.Value
    }

    if (
        $CurrentScope -ine $RequestedScope -and
        [string]::IsNullOrWhiteSpace($GroupDomainSid)
    ) {
        throw "SID de domaine du groupe introuvable"
    }

    if ($ScopeTransition -eq "Global vers Universal") {
        foreach ($ParentDn in @($Group.MemberOf)) {
            $ParentGroup = Get-ADGroup `
                -Identity $ParentDn `
                -Properties GroupScope, SID `
                -ErrorAction Stop

            $parent_group_scope = (
                [string]$ParentGroup.GroupScope
            ).Trim()

            $ParentChecks += [pscustomobject]@{
                group_dn = [string]$ParentGroup.DistinguishedName
                group_scope = $parent_group_scope
            }

            if ($parent_group_scope -eq "Global") {
                throw (
                    "Conversion Global vers Universal refusee : " +
                    "le groupe est membre du groupe global " +
                    [string]$ParentGroup.Name
                )
            }
        }
    }

    if ($ScopeTransition -eq "DomainLocal vers Universal") {
        foreach (
            $Member in @(
                Get-ADGroupMember `
                    -Identity $Group.DistinguishedName `
                    -ErrorAction Stop
            )
        ) {
            $MemberClass = (
                [string]$Member.ObjectClass
            ).Trim()

            if ($MemberClass -ieq "foreignSecurityPrincipal") {
                throw (
                    "Conversion DomainLocal vers Universal refusee : " +
                    "le groupe contient un foreignSecurityPrincipal"
                )
            }

            if ($MemberClass -ine "group") {
                continue
            }

            $MemberGroup = Get-ADGroup `
                -Identity $Member.DistinguishedName `
                -Properties GroupScope, SID `
                -ErrorAction Stop

            $member_group_scope = (
                [string]$MemberGroup.GroupScope
            ).Trim()

            $MemberChecks += [pscustomobject]@{
                group_dn = [string]$MemberGroup.DistinguishedName
                group_scope = $member_group_scope
            }

            if ($member_group_scope -eq "DomainLocal") {
                throw (
                    "Conversion DomainLocal vers Universal refusee : " +
                    "le groupe contient le groupe local de domaine " +
                    [string]$MemberGroup.Name
                )
            }
        }
    }

    if ($ScopeTransition -eq "Universal vers Global") {
        foreach (
            $Member in @(
                Get-ADGroupMember `
                    -Identity $Group.DistinguishedName `
                    -ErrorAction Stop
            )
        ) {
            $MemberClass = (
                [string]$Member.ObjectClass
            ).Trim()

            if ($MemberClass -ieq "foreignSecurityPrincipal") {
                throw (
                    "Conversion Universal vers Global refusee : " +
                    "un membre appartient a un autre domaine ou foret"
                )
            }

            $MemberDomainSid = ""

            if ($null -ne $Member.SID) {
                $MemberDomainSid = (
                    [string]$Member.SID.AccountDomainSid.Value
                )
            }

            $same_domain = (
                -not [string]::IsNullOrWhiteSpace($MemberDomainSid) -and
                $MemberDomainSid -ieq $GroupDomainSid
            )

            $member_group_scope = $null

            if ($MemberClass -ieq "group") {
                $MemberGroup = Get-ADGroup `
                    -Identity $Member.DistinguishedName `
                    -Properties GroupScope, SID `
                    -ErrorAction Stop

                $member_group_scope = (
                    [string]$MemberGroup.GroupScope
                ).Trim()

                if ($member_group_scope -eq "Universal") {
                    throw (
                        "Conversion Universal vers Global refusee : " +
                        "le groupe contient un groupe Universal"
                    )
                }

                $MemberDomainSid = (
                    [string]$MemberGroup.SID.AccountDomainSid.Value
                )

                $same_domain = (
                    -not [string]::IsNullOrWhiteSpace($MemberDomainSid) -and
                    $MemberDomainSid -ieq $GroupDomainSid
                )
            }

            $MemberChecks += [pscustomobject]@{
                object_dn = [string]$Member.DistinguishedName
                object_class = $MemberClass
                member_group_scope = $member_group_scope
                same_domain = $same_domain
            }

            if (-not $same_domain) {
                throw (
                    "Conversion Universal vers Global refusee : " +
                    "tous les membres doivent appartenir au meme domaine"
                )
            }
        }
    }

    if ($ScopeTransition -eq "Universal vers DomainLocal") {
        foreach ($ParentDn in @($Group.MemberOf)) {
            $ParentGroup = Get-ADGroup `
                -Identity $ParentDn `
                -Properties GroupScope, SID `
                -ErrorAction Stop

            $parent_group_scope = (
                [string]$ParentGroup.GroupScope
            ).Trim()

            $ParentDomainSid = ""

            if ($null -ne $ParentGroup.SID) {
                $ParentDomainSid = (
                    [string]$ParentGroup.SID.AccountDomainSid.Value
                )
            }

            $same_domain = (
                -not [string]::IsNullOrWhiteSpace($ParentDomainSid) -and
                $ParentDomainSid -ieq $GroupDomainSid
            )

            $ParentChecks += [pscustomobject]@{
                group_dn = [string]$ParentGroup.DistinguishedName
                parent_group_scope = $parent_group_scope
                same_domain = $same_domain
            }

            if ($parent_group_scope -eq "Universal") {
                throw (
                    "Conversion Universal vers DomainLocal refusee : " +
                    "le groupe est membre d'un groupe Universal"
                )
            }

            if (
                $parent_group_scope -eq "DomainLocal" -and
                -not $same_domain
            ) {
                throw (
                    "Conversion Universal vers DomainLocal refusee : " +
                    "le groupe est membre d'un groupe DomainLocal " +
                    "d'un autre domaine"
                )
            }
        }
    }

    $security_impact_warning = $null

    if ($CurrentCategory -ine $RequestedCategory) {
        if (
            $CurrentCategory -eq "Security" -and
            $RequestedCategory -eq "Distribution"
        ) {
            $security_impact_warning = (
                "Passage Security vers Distribution : " +
                "les ACE utilisant ce groupe ne seront plus " +
                "prises en compte par le systeme de securite."
            )
        }
        else {
            $security_impact_warning = (
                "Changement de categorie de groupe : verifier " +
                "les usages de securite et de messagerie."
            )
        }
    }

    return [pscustomobject]@{
        group_dn = [string]$Group.DistinguishedName
        group = [string]$Group.Name
        current_scope = $CurrentScope
        requested_scope = $RequestedScope
        current_category = $CurrentCategory
        requested_category = $RequestedCategory
        scope_changed = ($CurrentScope -ine $RequestedScope)
        category_changed = (
            $CurrentCategory -ine $RequestedCategory
        )
        transition = $ScopeTransition
        parent_checks = @($ParentChecks)
        member_checks = @($MemberChecks)
        security_impact_warning = $security_impact_warning
    }
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
        "operatingSystem",
        "operatingSystemVersion",
        "operatingSystemServicePack",
        "displayName",
        "givenName",
        "personalTitle",
        "initials",
        "preferredLanguage",
        "sn",
        "mail",
        "wWWHomePage",
        "info",
        "uidNumber",
        "gidNumber",
        "unixHomeDirectory",
        "loginShell",
        "gecos",
        "samAccountName",
        "userPrincipalName",
        "accountExpires",
        "userWorkstations",
        "logonHours",
        "passwordNeverExpires",
        "cannotChangePassword",
        "smartcardLogonRequired",
        "accountNotDelegated",
        "msTSAllowLogon",
        "msTSProfilePath",
        "msTSHomeDirectory",
        "msTSHomeDrive",
        "msTSInitialProgram",
        "msTSWorkDirectory",
        "title",
        "department",
        "division",
        "company",
        "telephoneNumber",
        "homePhone",
        "facsimileTelephoneNumber",
        "pager",
        "ipPhone",
        "mobile",
        "physicalDeliveryOfficeName",
        "employeeID",
        "employeeNumber",
        "manager",
        "profilePath",
        "scriptPath",
        "homeDirectory",
        "homeDrive",
        "groupScope",
        "groupCategory",
        "managedBy",
        "protectedFromAccidentalDeletion",
        "streetAddress",
        "postalCode",
        "postOfficeBox",
        "l",
        "st",
        "c",
        "co",
        "countryCode"
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

    $Object = Resolve-EitasAdAdminObject `
        -Config $Config `
        -Identity $ObjectIdentity

    $ObjectDn = (
        [string]$Object.DistinguishedName
    ).Trim()

    $ObjectClassName = (
        [string]$Object.ObjectClass
    ).Trim().ToLowerInvariant()

    if ($Properties.ContainsKey("managedBy")) {
        $ManagedByPreviewValue = (
            [string](
                Repair-EitasTextEncoding `
                    -Value $Properties["managedBy"]
            )
        ).Trim()

        if (
            -not [string]::IsNullOrWhiteSpace(
                $ManagedByPreviewValue
            )
        ) {
            $ManagedByPreview =
                Resolve-EitasAdAdminManagedByUser `
                    -Config $Config `
                    -Identity $ManagedByPreviewValue

            $Properties["managedBy"] = (
                [string]$ManagedByPreview.DistinguishedName
            ).Trim()
        } else {
            $Properties["managedBy"] = ""
        }

        if (
            @(
                "group",
                "computer",
                "organizationalunit"
            ) -notcontains $ObjectClassName
        ) {
            throw "managedBy est réservé aux groupes, ordinateurs et unités d'organisation"
        }
    }

    $GroupTransitionPreview = $null

    if (
        $Properties.ContainsKey("groupScope") -or
        $Properties.ContainsKey("groupCategory")
    ) {
        $GroupTransitionPreview =
            Assert-EitasAdAdminGroupUpdateTransitionSafe `
                -Config $Config `
                -ObjectIdentity $ObjectIdentity `
                -Properties $Properties
    }

    $CurrentPostOfficeBoxes = @()

    if ($Properties.ContainsKey("postOfficeBox")) {
        $CurrentPostOfficeBoxes = @(
            (
                Get-ADObject `
                    -Identity $ObjectDn `
                    -Properties postOfficeBox `
                    -ErrorAction Stop
            ).postOfficeBox |
                ForEach-Object {
                    ([string]$_).Trim()
                } |
                Where-Object {
                    -not [string]::IsNullOrWhiteSpace($_)
                }
        )
    }

    $PersonNameProperties = @(
        "givenName",
        "initials",
        "sn"
    )

    $HasPersonNameChanges = @(
        $Properties.Keys |
            Where-Object {
                $PersonNameProperties -contains [string]$_
            }
    ).Count -gt 0

    $PersonObjectClass = (
        [string]$Object.ObjectClass
    ).Trim().ToLowerInvariant()

    if (
        $HasPersonNameChanges -and
        @(
            "user",
            "contact"
        ) -notcontains $PersonObjectClass
    ) {
        throw (
            "givenName, initials et sn sont " +
            "réservés aux utilisateurs et contacts"
        )
    }

    $AdvancedUserProperties = @(
        "personalTitle",
        "preferredLanguage",
        "uidNumber",
        "gidNumber",
        "unixHomeDirectory",
        "loginShell",
        "gecos"
    )

    $HasAdvancedUserChanges = @(
        $Properties.Keys |
            Where-Object {
                $AdvancedUserProperties -contains [string]$_
            }
    ).Count -gt 0

    if (
        $HasAdvancedUserChanges -and
        $PersonObjectClass -ne "user"
    ) {
        throw (
            "Les proprietes avancees et POSIX sont " +
            "reservees aux utilisateurs"
        )
    }

    $AdvancedProfileTextProperties = @(
        "personalTitle",
        "initials",
        "preferredLanguage",
        "info",
        "unixHomeDirectory",
        "loginShell",
        "gecos"
    )

    $PosixIntegerProperties = @(
        "uidNumber",
        "gidNumber"
    )

    $ProfileProperties = @(
        "profilePath",
        "scriptPath",
        "homeDirectory",
        "homeDrive"
    )

    $HasProfileChanges = @(
        $Properties.Keys |
            Where-Object {
                $ProfileProperties -contains [string]$_
            }
    ).Count -gt 0

    if (
        $HasProfileChanges -and
        $PersonObjectClass -ne "user"
    ) {
        throw (
            "profilePath, scriptPath, homeDirectory " +
            "et homeDrive sont réservés aux utilisateurs"
        )
    }

    $AccountProperties = @(
        "userPrincipalName",
        "accountExpires",
        "userWorkstations",
        "logonHours",
        "passwordNeverExpires",
        "cannotChangePassword",
        "smartcardLogonRequired",
        "accountNotDelegated"
    )

    $HasAccountChanges = @(
        $Properties.Keys |
            Where-Object {
                $AccountProperties -contains [string]$_
            }
    ).Count -gt 0

    if (
        $HasAccountChanges -and
        $PersonObjectClass -ne "user"
    ) {
        throw (
            "userPrincipalName, accountExpires, " +
            "userWorkstations, logonHours, " +
            "passwordNeverExpires et " +
            "cannotChangePassword sont " +
            "réservés aux utilisateurs"
        )
    }

    $RdsProperties = @(
        "msTSAllowLogon",
        "msTSProfilePath",
        "msTSHomeDirectory",
        "msTSHomeDrive",
        "msTSInitialProgram",
        "msTSWorkDirectory"
    )

    $RdsTextProperties = @(
        "msTSProfilePath",
        "msTSHomeDirectory",
        "msTSHomeDrive",
        "msTSInitialProgram",
        "msTSWorkDirectory"
    )

    $HasRdsChanges = @(
        $Properties.Keys |
            Where-Object {
                $RdsProperties -contains [string]$_
            }
    ).Count -gt 0

    if (
        $HasRdsChanges -and
        $PersonObjectClass -ne "user"
    ) {
        throw (
            "Les proprietes RDS msTS sont reservees " +
            "aux utilisateurs"
        )
    }

    $MaximumAttributeLengths = @{
        personalTitle = 64
        initials = 6
        preferredLanguage = 32767
        wWWHomePage = 2048
        telephoneNumber = 64
        homePhone = 64
        facsimileTelephoneNumber = 64
        pager = 64
        mobile = 64
        ipPhone = 64
        info = 1024
        unixHomeDirectory = 2048
        loginShell = 1024
        gecos = 10240
        postOfficeBox = 40
        co = 128
    }

    $Replace = @{}
    $Clear = @()

    $HasCountryTripletChanges = (
        $Properties.ContainsKey("c") -or
        $Properties.ContainsKey("countryCode")
    )

    if ($HasCountryTripletChanges) {
        foreach (
            $RequiredCountryKey in @(
                "c",
                "co",
                "countryCode"
            )
        ) {
            if (
                -not $Properties.ContainsKey(
                    $RequiredCountryKey
                )
            ) {
                throw (
                    "Le pays doit être envoyé avec " +
                    "c, co et countryCode"
                )
            }
        }

        $CountryAlpha2 = (
            [string](
                Repair-EitasTextEncoding `
                    -Value $Properties["c"]
            )
        ).Trim().ToUpperInvariant()

        $CountryName = (
            [string](
                Repair-EitasTextEncoding `
                    -Value $Properties["co"]
            )
        ).Trim()

        $CountryNumericValue = (
            [string]$Properties["countryCode"]
        ).Trim()

        $EmptyCountryCount = @(
            @(
                [string]::IsNullOrWhiteSpace(
                    $CountryAlpha2
                ),
                [string]::IsNullOrWhiteSpace(
                    $CountryName
                ),
                [string]::IsNullOrWhiteSpace(
                    $CountryNumericValue
                )
            ) |
                Where-Object {
                    $_
                }
        ).Count

        if ($EmptyCountryCount -eq 3) {
            $Clear += @(
                "c",
                "co",
                "countryCode"
            )
        } elseif ($EmptyCountryCount -gt 0) {
            throw (
                "c, co et countryCode doivent être " +
                "tous renseignés ou tous vidés"
            )
        } else {
            if (
                $CountryAlpha2 -notmatch "^[A-Z]{2}$"
            ) {
                throw (
                    "c doit être un code pays ISO alpha-2"
                )
            }

            if ($CountryName.Length -gt 128) {
                throw (
                    "co est limité à 128 caractères"
                )
            }

            $CountryNumericCode = 0

            if (
                -not [int]::TryParse(
                    $CountryNumericValue,
                    [ref]$CountryNumericCode
                ) -or
                $CountryNumericCode -lt 0 -or
                $CountryNumericCode -gt 65535
            ) {
                throw (
                    "countryCode doit être un entier " +
                    "compris entre 0 et 65535"
                )
            }

            $Replace["c"] = $CountryAlpha2
            $Replace["co"] = $CountryName
            $Replace["countryCode"] = (
                $CountryNumericCode
            )
        }
    }

    $GroupScope = $null
    $GroupCategory = $null
    $GroupSamAccountName = $null
    $ComputerProperties = @{}
    $ComputerClear = @()
    $ManagedBy = $null
    $ClearManagedBy = $false
    $ProtectedFromAccidentalDeletion = $null
    $UserPrincipalNameValue = $null
    $AccountExpirationDate = $null
    $ClearAccountExpiration = $false
    $UserWorkstationsValue = $null
    $ClearUserWorkstations = $false
    $LogonHoursBytes = $null
    $ClearLogonHours = $false
    $PasswordNeverExpiresValue = $null
    $CannotChangePasswordValue = $null
    $SmartcardLogonRequiredValue = $null
    $AccountNotDelegatedValue = $null

    foreach ($Key in $Properties.Keys) {
        $RawValue = $Properties[$Key]

        if (
            $HasCountryTripletChanges -and
            $Key -in @(
                "c",
                "co",
                "countryCode"
            )
        ) {
            continue
        }

        if (
            $PosixIntegerProperties -contains
            [string]$Key
        ) {
            $IntegerText = (
                [string]$RawValue
            ).Trim()

            if (
                [string]::IsNullOrWhiteSpace(
                    $IntegerText
                )
            ) {
                $Clear += $Key
                continue
            }

            $IntegerValue = 0

            if (
                -not [int]::TryParse(
                    $IntegerText,
                    [ref]$IntegerValue
                )
            ) {
                throw (
                    "$Key doit etre un entier Integer32"
                )
            }

            $Replace[$Key] = $IntegerValue
            continue
        }

        if ($Key -eq "postOfficeBox") {
            if ($CurrentPostOfficeBoxes.Count -gt 1) {
                throw (
                    "postOfficeBox contient plusieurs " +
                    "valeurs. Utiliser l’éditeur LDAP C2."
                )
            }

            $PostOfficeBoxValue = (
                [string](
                    Repair-EitasTextEncoding `
                        -Value $RawValue
                )
            ).Trim()

            if (
                [string]::IsNullOrWhiteSpace(
                    $PostOfficeBoxValue
                )
            ) {
                $Clear += "postOfficeBox"
            } else {
                if (
                    $PostOfficeBoxValue.Length -gt 40
                ) {
                    throw (
                        "postOfficeBox est limité à " +
                        "40 caractères"
                    )
                }

                $Replace["postOfficeBox"] = @(
                    $PostOfficeBoxValue
                )
            }

            continue
        }

        if ($Key -eq "protectedFromAccidentalDeletion") {
            if ($RawValue -isnot [bool]) {
                throw "protectedFromAccidentalDeletion doit être un booléen"
            }

            $ProtectedFromAccidentalDeletion = [bool]$RawValue
            continue
        }

        if ($Key -eq "msTSAllowLogon") {
            if ($null -eq $RawValue) {
                $Clear += "msTSAllowLogon"
                continue
            }

            if ($RawValue -isnot [bool]) {
                throw (
                    "msTSAllowLogon doit etre un booleen " +
                    "JSON ou null pour effacer la valeur"
                )
            }

            $Replace["msTSAllowLogon"] = [bool]$RawValue
            continue
        }

        if ($Key -in $RdsTextProperties) {
            if (
                $null -ne $RawValue -and
                $RawValue -isnot [string]
            ) {
                throw (
                    "$Key doit contenir une seule chaine " +
                    "de caracteres"
                )
            }

            $RdsTextValue = (
                [string](
                    Repair-EitasTextEncoding `
                        -Value $RawValue
                )
            ).Trim()

            if (
                [string]::IsNullOrWhiteSpace(
                    $RdsTextValue
                )
            ) {
                $Clear += $Key
            } else {
                if ($Key -eq "msTSHomeDrive") {
                    $RdsTextValue = (
                        $RdsTextValue.ToUpperInvariant()
                    )

                    if (
                        $RdsTextValue -notmatch "^[A-Z]:$"
                    ) {
                        throw (
                            "msTSHomeDrive doit etre une lettre " +
                            "de lecteur suivie de deux-points, " +
                            "par exemple R:"
                        )
                    }
                }

                if ($RdsTextValue.Length -gt 32767) {
                    throw (
                        "$Key est limite a 32767 " +
                        "caracteres par le schema AD"
                    )
                }

                $Replace[$Key] = $RdsTextValue
            }

            continue
        }

        if (
            $Key -in @(
                "passwordNeverExpires",
                "cannotChangePassword",
                "smartcardLogonRequired",
                "accountNotDelegated"
            )
        ) {
            if ($RawValue -isnot [bool]) {
                throw "$Key doit être un booléen JSON"
            }

            switch ($Key) {
                "passwordNeverExpires" {
                    $PasswordNeverExpiresValue = [bool]$RawValue
                }
                "cannotChangePassword" {
                    $CannotChangePasswordValue = [bool]$RawValue
                }
                "smartcardLogonRequired" {
                    $SmartcardLogonRequiredValue = [bool]$RawValue
                }
                "accountNotDelegated" {
                    $AccountNotDelegatedValue = [bool]$RawValue
                }
            }

            continue
        }

        if (
            $Key -in $AdvancedProfileTextProperties -and
            $null -ne $RawValue -and
            $RawValue -isnot [string]
        ) {
            throw (
                "$Key doit contenir une seule chaine " +
                "de caracteres"
            )
        }

        $Value = Repair-EitasTextEncoding -Value $RawValue

        if (
            $null -ne $Value -and
            $MaximumAttributeLengths.ContainsKey($Key) -and
            ([string]$Value).Length -gt
                [int]$MaximumAttributeLengths[$Key]
        ) {
            throw (
                "$Key est limité à " +
                "$($MaximumAttributeLengths[$Key]) caractères"
            )
        }

        if ($Key -eq "samAccountName") {
            $GroupSamAccountName = (
                [string]$Value
            ).Trim()

            if (
                [string]::IsNullOrWhiteSpace(
                    $GroupSamAccountName
                )
            ) {
                throw "samAccountName ne peut pas être vide"
            }

            if ($GroupSamAccountName.Length -gt 256) {
                throw "samAccountName est limité à 256 caractères par le schéma AD"
            }
        } elseif (
            $Key -in @(
                "operatingSystem",
                "operatingSystemVersion",
                "operatingSystemServicePack"
            )
        ) {
            if (
                $null -eq $Value -or
                [string]::IsNullOrWhiteSpace(
                    [string]$Value
                )
            ) {
                $ComputerClear += $Key
            } else {
                $ComputerProperties[$Key] = [string]$Value
            }
        } elseif ($Key -eq "userPrincipalName") {
            $UserPrincipalNameValue = (
                [string]$Value
            ).Trim()

            if (
                [string]::IsNullOrWhiteSpace(
                    $UserPrincipalNameValue
                )
            ) {
                throw (
                    "userPrincipalName ne peut pas être vide"
                )
            }

            if ($UserPrincipalNameValue.Length -gt 1024) {
                throw (
                    "userPrincipalName est limité à " +
                    "1024 caractères par le schéma AD"
                )
            }

            if (
                $UserPrincipalNameValue -notmatch
                "^[A-Za-z0-9._-]+@[A-Za-z0-9.-]+$"
            ) {
                throw "userPrincipalName doit être un UPN valide"
            }
        } elseif ($Key -eq "accountExpires") {
            $AccountExpirationText = (
                [string]$Value
            ).Trim()

            if (
                [string]::IsNullOrWhiteSpace(
                    $AccountExpirationText
                )
            ) {
                $ClearAccountExpiration = $true
            } else {
                $ParsedExpirationDate = [datetime]::MinValue

                $DateParsed = [datetime]::TryParseExact(
                    $AccountExpirationText,
                    "yyyy-MM-dd",
                    [System.Globalization.CultureInfo]::InvariantCulture,
                    [System.Globalization.DateTimeStyles]::None,
                    [ref]$ParsedExpirationDate
                )

                if (-not $DateParsed) {
                    throw (
                        "accountExpires doit contenir une " +
                        "date valide au format AAAA-MM-JJ"
                    )
                }

                $AccountExpirationDate = $ParsedExpirationDate.Date.AddDays(1).AddSeconds(-1)
            }
        } elseif ($Key -eq "userWorkstations") {
            $WorkstationsText = (
                [string]$Value
            ).Trim()

            if (
                [string]::IsNullOrWhiteSpace(
                    $WorkstationsText
                )
            ) {
                $ClearUserWorkstations = $true
            } else {
                $NormalizedWorkstations =
                    New-Object `
                        "System.Collections.Generic.List[string]"

                foreach (
                    $RawWorkstationName in @(
                        $WorkstationsText -split "[,;]"
                    )
                ) {
                    $WorkstationName = (
                        [string]$RawWorkstationName
                    ).Trim().ToUpperInvariant()

                    if (
                        [string]::IsNullOrWhiteSpace(
                            $WorkstationName
                        )
                    ) {
                        continue
                    }

                    if (
                        $WorkstationName.Length -gt 15 -or
                        $WorkstationName -notmatch (
                            "^[A-Z0-9]" +
                            "(?:[A-Z0-9-]*[A-Z0-9])?$"
                        )
                    ) {
                        throw (
                            "Nom NetBIOS de station invalide : " +
                            $WorkstationName
                        )
                    }

                    if (
                        -not $NormalizedWorkstations.Contains(
                            $WorkstationName
                        )
                    ) {
                        $NormalizedWorkstations.Add(
                            $WorkstationName
                        )
                    }
                }

                $UserWorkstationsValue = (
                    $NormalizedWorkstations -join ","
                )

                if ($UserWorkstationsValue.Length -gt 1024) {
                    throw (
                        "userWorkstations est limité à " +
                        "1024 caractères par le schéma AD"
                    )
                }
            }
        } elseif ($Key -eq "logonHours") {
            $LogonHoursText = (
                [string]$Value
            ).Trim()

            if (
                [string]::IsNullOrWhiteSpace(
                    $LogonHoursText
                )
            ) {
                $ClearLogonHours = $true
            } else {
                $LogonHourTokens = @(
                    $LogonHoursText -split "[\s,;]+" |
                        Where-Object {
                            -not [string]::IsNullOrWhiteSpace(
                                [string]$_
                            )
                        }
                )

                if ($LogonHourTokens.Count -ne 21) {
                    throw (
                        "logonHours doit contenir exactement " +
                        "21 octets hexadécimaux"
                    )
                }

                [byte[]]$ParsedLogonHours =
                    New-Object byte[] 21

                for (
                    $Index = 0;
                    $Index -lt 21;
                    $Index++
                ) {
                    $Token = (
                        [string]$LogonHourTokens[$Index]
                    ).Trim()

                    if (
                        $Token -notmatch
                        "^[0-9A-Fa-f]{2}$"
                    ) {
                        throw (
                            "Octet logonHours invalide : " +
                            $Token
                        )
                    }

                    $ParsedLogonHours[$Index] = (
                        [System.Convert]::ToByte(
                            $Token,
                            16
                        )
                    )
                }

                $LogonHoursBytes = $ParsedLogonHours
            }
        } elseif ($Key -eq "homeDrive") {
            if (
                $null -eq $Value -or
                [string]::IsNullOrWhiteSpace(
                    [string]$Value
                )
            ) {
                $Clear += "homeDrive"
            } else {
                $HomeDrive = (
                    [string]$Value
                ).Trim().ToUpperInvariant()

                if (
                    $HomeDrive -notmatch "^[A-Z]:$"
                ) {
                    throw (
                        "homeDrive doit être une lettre " +
                        "de lecteur suivie de deux-points, " +
                        "par exemple H:"
                    )
                }

                $Replace["homeDrive"] = $HomeDrive
            }
        } elseif ($Key -eq "groupScope") {
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

    $HasGroupSamChanges =
        $null -ne $GroupSamAccountName

    if (
        $HasGroupSamChanges -and
        @(
            "group",
            "computer"
        ) -notcontains $ObjectClassName
    ) {
        throw "samAccountName est réservé aux groupes et ordinateurs dans ce formulaire"
    }

    if (
        $HasGroupSamChanges -and
        $ObjectClassName -eq "computer" -and
        -not $GroupSamAccountName.EndsWith(
            '$'
        )
    ) {
        $GroupSamAccountName += '$'
    }

    if (
        $HasGroupSamChanges -and
        $ObjectClassName -eq "computer" -and
        $GroupSamAccountName.Length -gt 256
    ) {
        throw "samAccountName ordinateur est limité à 256 caractères, suffixe `$ compris"
    }

    $HasComputerSystemChanges = (
        $ComputerProperties.Count -gt 0 -or
        $ComputerClear.Count -gt 0
    )

    if (
        $HasComputerSystemChanges -and
        $ObjectClassName -ne "computer"
    ) {
        throw "Les propriétés de système d’exploitation sont réservées aux ordinateurs"
    }

    $HasInfoChanges =
        $Properties.ContainsKey("info")

    if (
        $HasInfoChanges -and
        @(
            "user",
            "group",
            "contact"
        ) -notcontains $ObjectClassName
    ) {
        throw (
            "info est reserve aux utilisateurs, " +
            "groupes et contacts"
        )
    }

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
        @(
            "organizationalunit",
            "computer",
            "contact"
        ) -notcontains $ObjectClassName
    ) {
        throw "La protection contre la suppression accidentelle est réservée aux unités d'organisation, ordinateurs et contacts"
    }


    if ($null -ne $GroupSamAccountName) {
        $RootDse = Get-ADRootDSE `
            -ErrorAction Stop

        $EscapedSamAccountName = (
            Escape-EitasLdapFilterValue `
                -Value $GroupSamAccountName
        )

        $SamConflict = Get-ADObject `
            -SearchBase $RootDse.defaultNamingContext `
            -SearchScope Subtree `
            -LDAPFilter "(sAMAccountName=$EscapedSamAccountName)" `
            -Properties distinguishedName `
            -ResultSetSize 2 `
            -ErrorAction Stop |
            Where-Object {
                [string]$_.DistinguishedName -ine $ObjectDn
            } |
            Select-Object -First 1

        if ($null -ne $SamConflict) {
            throw "Un objet Active Directory utilise déjà le nom de compte antérieur à Windows 2000 : $GroupSamAccountName"
        }
    }

    if ($null -ne $UserPrincipalNameValue) {
        $AtIndex = $UserPrincipalNameValue.LastIndexOf("@")

        if (
            $AtIndex -lt 1 -or
            $AtIndex -ge ($UserPrincipalNameValue.Length - 1)
        ) {
            throw "Suffixe UPN introuvable"
        }

        $RequestedUpnSuffix = (
            $UserPrincipalNameValue.Substring(
                $AtIndex + 1
            )
        )

        $Domain = Get-ADDomain `
            -ErrorAction Stop

        $Forest = Get-ADForest `
            -ErrorAction Stop

        $AllowedUpnSuffixes = @(
            @(
                [string]$Domain.DNSRoot
            ) +
            @(
                $Forest.UPNSuffixes
            ) |
                ForEach-Object {
                    ([string]$_).Trim()
                } |
                Where-Object {
                    -not [string]::IsNullOrWhiteSpace($_)
                } |
                Sort-Object -Unique
        )

        if (
            $AllowedUpnSuffixes -inotcontains
            $RequestedUpnSuffix
        ) {
            throw (
                "Suffixe UPN non autorisé : " +
                $RequestedUpnSuffix
            )
        }

        $RootDse = Get-ADRootDSE `
            -ErrorAction Stop

        $EscapedUpn = Escape-EitasLdapFilterValue `
            -Value $UserPrincipalNameValue

        $UpnConflict = Get-ADUser `
            -SearchBase $RootDse.defaultNamingContext `
            -SearchScope Subtree `
            -LDAPFilter "(userPrincipalName=$EscapedUpn)" `
            -Properties distinguishedName `
            -ResultSetSize 2 `
            -ErrorAction Stop |
            Where-Object {
                [string]$_.DistinguishedName -ine $ObjectDn
            } |
            Select-Object -First 1

        if ($null -ne $UpnConflict) {
            throw (
                "Un utilisateur Active Directory utilise " +
                "déjà cet UPN : $UserPrincipalNameValue"
            )
        }
    }

    if ($null -ne $UserWorkstationsValue) {
        foreach (
            $WorkstationName in @(
                $UserWorkstationsValue -split ","
            )
        ) {
            try {
                Get-ADComputer `
                    -Identity $WorkstationName `
                    -ErrorAction Stop |
                    Out-Null
            }
            catch {
                throw (
                    "Ordinateur Active Directory introuvable " +
                    "pour userWorkstations : " +
                    $WorkstationName
                )
            }
        }
    }

    if ($Mode -ne "Production") {
        return [pscustomobject]@{
            action = "update_object_properties"
            simulated = $true
            object_identity = $ObjectIdentity
            properties = $Properties
            group_transition = $GroupTransitionPreview
            message = "Simulation modification propriétés objet AD"
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

    $SetUserParameters = @{
        Identity = $ObjectDn
        ErrorAction = "Stop"
    }

    if ($null -ne $UserPrincipalNameValue) {
        $SetUserParameters["UserPrincipalName"] = (
            $UserPrincipalNameValue
        )
    }

    if ($null -ne $AccountExpirationDate) {
        $SetUserParameters["AccountExpirationDate"] = (
            $AccountExpirationDate
        )
    }

    if ($null -ne $PasswordNeverExpiresValue) {
        $SetUserParameters["PasswordNeverExpires"] = (
            [bool]$PasswordNeverExpiresValue
        )
    }

    if ($null -ne $CannotChangePasswordValue) {
        $SetUserParameters["CannotChangePassword"] = (
            [bool]$CannotChangePasswordValue
        )
    }

    if ($null -ne $SmartcardLogonRequiredValue) {
        $SetUserParameters["SmartcardLogonRequired"] = (
            [bool]$SmartcardLogonRequiredValue
        )
    }

    if ($null -ne $AccountNotDelegatedValue) {
        $SetUserParameters["AccountNotDelegated"] = (
            [bool]$AccountNotDelegatedValue
        )
    }

    if ($SetUserParameters.Count -gt 2) {
        Set-ADUser @SetUserParameters
    }

    if ($ClearAccountExpiration) {
        Clear-ADAccountExpiration `
            -Identity $ObjectDn `
            -ErrorAction Stop
    }

    if ($null -ne $UserWorkstationsValue) {
        Set-ADUser `
            -Identity $ObjectDn `
            -LogonWorkstations $UserWorkstationsValue `
            -ErrorAction Stop
    }

    if ($ClearUserWorkstations) {
        Set-ADUser `
            -Identity $ObjectDn `
            -Clear @("userWorkstations") `
            -ErrorAction Stop
    }

    if ($null -ne $LogonHoursBytes) {
        Set-ADUser `
            -Identity $ObjectDn `
            -Replace @{
                logonHours = [byte[]]$LogonHoursBytes
            } `
            -ErrorAction Stop
    }

    if ($ClearLogonHours) {
        Set-ADUser `
            -Identity $ObjectDn `
            -Clear @("logonHours") `
            -ErrorAction Stop
    }

    if (
        $HasGroupSpecificChanges -or
        (
            $HasGroupSamChanges -and
            $ObjectClassName -eq "group"
        ) -or
        (
            $HasManagedByChanges -and
            $ObjectClassName -eq "group"
        )
    ) {
        $SetGroupParameters = @{
            Identity = $ObjectDn
            ErrorAction = "Stop"
        }

        if ($null -ne $GroupSamAccountName) {
            $SetGroupParameters["SamAccountName"] = (
                $GroupSamAccountName
            )
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

    if ($ObjectClassName -eq "computer") {
        $SetComputerParameters = @{
            Identity = $ObjectDn
            ErrorAction = "Stop"
        }

        if ($HasGroupSamChanges) {
            $SetComputerParameters["SamAccountName"] = `
                $GroupSamAccountName
        }

        foreach ($ComputerKey in $ComputerProperties.Keys) {
            $SetComputerParameters[$ComputerKey] = `
                $ComputerProperties[$ComputerKey]
        }

        if ($null -ne $ManagedBy) {
            $SetComputerParameters["ManagedBy"] = $ManagedBy
        }

        if ($SetComputerParameters.Count -gt 2) {
            Set-ADComputer @SetComputerParameters
        }

        $ComputerClearAttributes = @(
            $ComputerClear
        )

        if ($ClearManagedBy) {
            $ComputerClearAttributes += "managedBy"
        }

        if ($ComputerClearAttributes.Count -gt 0) {
            Set-ADComputer `
                -Identity $ObjectDn `
                -Clear $ComputerClearAttributes `
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
        if ($ObjectClassName -eq "organizationalunit") {
            Set-ADOrganizationalUnit `
                -Identity $ObjectDn `
                -ProtectedFromAccidentalDeletion $ProtectedFromAccidentalDeletion `
                -ErrorAction Stop
        } elseif (
            $ObjectClassName -in @(
                "computer",
                "contact"
            )
        ) {
            Set-ADObject `
                -Identity $ObjectDn `
                -ProtectedFromAccidentalDeletion $ProtectedFromAccidentalDeletion `
                -ErrorAction Stop
        }
    }


    $UpdatedObject = Get-ADObject `
        -Identity $ObjectDn `
        -Properties objectClass, sAMAccountName, userPrincipalName, accountExpires, userWorkstations, logonHours, directReports, displayName, givenName, personalTitle, initials, preferredLanguage, sn, description, location, mail, wWWHomePage, info, uidNumber, gidNumber, unixHomeDirectory, loginShell, gecos, title, department, division, company, telephoneNumber, homePhone, facsimileTelephoneNumber, pager, ipPhone, mobile, physicalDeliveryOfficeName, employeeID, employeeNumber, manager, profilePath, scriptPath, homeDirectory, homeDrive, msTSAllowLogon, msTSProfilePath, msTSHomeDirectory, msTSHomeDrive, msTSInitialProgram, msTSWorkDirectory, managedBy, streetAddress, postalCode, postOfficeBox, l, st, c, co, countryCode, operatingSystem, operatingSystemVersion, operatingSystemServicePack, ProtectedFromAccidentalDeletion `
        -ErrorAction Stop

    $UpdatedGroupScope = $null
    $UpdatedGroupCategory = $null
    $UpdatedManagedBy = [string]$UpdatedObject.managedBy
    $UpdatedSamAccountName = $null
    $UpdatedProtectedFromAccidentalDeletion = $null
    $UpdatedPasswordNeverExpires = $null
    $UpdatedCannotChangePassword = $null
    $UpdatedSmartcardLogonRequired = $null
    $UpdatedAccountNotDelegated = $null
    $UpdatedMsTsAllowLogon = $null

    if ($ObjectClassName -eq "user") {
        $UpdatedUser = Get-ADUser `
            -Identity $ObjectDn `
            -Properties `
                PasswordNeverExpires, `
                CannotChangePassword, `
                SmartcardLogonRequired, `
                AccountNotDelegated `
            -ErrorAction Stop

        $UpdatedPasswordNeverExpires = (
            [bool]$UpdatedUser.PasswordNeverExpires
        )

        $UpdatedCannotChangePassword = (
            [bool]$UpdatedUser.CannotChangePassword
        )

        $UpdatedSmartcardLogonRequired = (
            [bool]$UpdatedUser.SmartcardLogonRequired
        )

        $UpdatedAccountNotDelegated = (
            [bool]$UpdatedUser.AccountNotDelegated
        )

        if ($null -ne $UpdatedObject.msTSAllowLogon) {
            $UpdatedMsTsAllowLogon = (
                [bool]$UpdatedObject.msTSAllowLogon
            )
        }
    }

    if ([string]$Object.ObjectClass -eq "group") {
        $UpdatedGroup = Get-ADGroup `
            -Identity $ObjectDn `
            -Properties ManagedBy, sAMAccountName `
            -ErrorAction Stop

        $UpdatedSamAccountName = (
            [string]$UpdatedGroup.SamAccountName
        )
        $UpdatedGroupScope = [string]$UpdatedGroup.GroupScope
        $UpdatedGroupCategory = [string]$UpdatedGroup.GroupCategory
    }

    if ($ObjectClassName -eq "computer") {
        $UpdatedSamAccountName = (
            [string]$UpdatedObject.sAMAccountName
        )
    }

    if (
        $ObjectClassName -in @(
            "computer",
            "contact"
        )
    ) {
        $UpdatedProtectedFromAccidentalDeletion = `
            [bool]$UpdatedObject.ProtectedFromAccidentalDeletion
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
        sam_account_name = $UpdatedSamAccountName
        personal_title = (
            [string]$UpdatedObject.personalTitle
        )
        initials = (
            [string]$UpdatedObject.initials
        )
        preferred_language = (
            [string]$UpdatedObject.preferredLanguage
        )
        info = (
            [string]$UpdatedObject.info
        )
        uid_number = if (
            $null -eq $UpdatedObject.uidNumber -or
            [string]::IsNullOrWhiteSpace(
                [string]$UpdatedObject.uidNumber
            )
        ) {
            $null
        } else {
            [Convert]::ToInt32(
                $UpdatedObject.uidNumber
            )
        }
        gid_number = if (
            $null -eq $UpdatedObject.gidNumber -or
            [string]::IsNullOrWhiteSpace(
                [string]$UpdatedObject.gidNumber
            )
        ) {
            $null
        } else {
            [Convert]::ToInt32(
                $UpdatedObject.gidNumber
            )
        }
        unix_home_directory = (
            [string]$UpdatedObject.unixHomeDirectory
        )
        login_shell = (
            [string]$UpdatedObject.loginShell
        )
        gecos = (
            [string]$UpdatedObject.gecos
        )
        user_principal_name = (
            [string]$UpdatedObject.userPrincipalName
        )
        account_expires = (
            [string]$UpdatedObject.accountExpires
        )
        user_workstations = (
            [string]$UpdatedObject.userWorkstations
        )
        logon_hours = (
            @($UpdatedObject.logonHours) |
                ForEach-Object {
                    ([byte]$_).ToString("X2")
                }
        ) -join " "
        password_never_expires = (
            $UpdatedPasswordNeverExpires
        )
        cannot_change_password = (
            $UpdatedCannotChangePassword
        )
        smartcard_logon_required = (
            $UpdatedSmartcardLogonRequired
        )
        account_not_delegated = (
            $UpdatedAccountNotDelegated
        )
        ms_ts_allow_logon = $UpdatedMsTsAllowLogon
        ms_ts_profile_path = (
            [string]$UpdatedObject.msTSProfilePath
        )
        ms_ts_home_directory = (
            [string]$UpdatedObject.msTSHomeDirectory
        )
        ms_ts_home_drive = (
            [string]$UpdatedObject.msTSHomeDrive
        )
        ms_ts_initial_program = (
            [string]$UpdatedObject.msTSInitialProgram
        )
        ms_ts_work_directory = (
            [string]$UpdatedObject.msTSWorkDirectory
        )
        direct_reports = @(
            $UpdatedObject.directReports
        )
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

    $Object = Resolve-EitasAdAdminObject -Config $Config -Identity $ObjectIdentity

    $ObjectDn = ([string]$Object.DistinguishedName).Trim()

    if ($ObjectDn -ine $ConfirmDn) {
        throw "Confirmation DN invalide. DN réel : $ObjectDn"
    }

    $IsOu = ([string]$Object.ObjectClass -ieq "organizationalUnit")
    $IsContact = ([string]$Object.ObjectClass -ieq "contact")
    $OuEmptyVerified = $false
    $OuWasProtected = $false
    $ContactWasProtected = $false

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

        $OuWasProtected = [bool]$Ou.ProtectedFromAccidentalDeletion
    }

    if ($IsContact) {
        $ContactBeforeDelete = Get-ADObject `
            -Identity $ObjectDn `
            -Properties ProtectedFromAccidentalDeletion `
            -ErrorAction Stop

        $ContactWasProtected = (
            [bool]$ContactBeforeDelete.ProtectedFromAccidentalDeletion
        )
    }

    if ($Mode -ne "Production") {
        return [pscustomobject]@{
            action = "delete_object"
            simulated = $true
            object_identity = $ObjectIdentity
            confirm_dn = $ConfirmDn
            ou_empty_verified = $OuEmptyVerified
            ou_was_protected = $OuWasProtected
            contact_was_protected = $ContactWasProtected
            message = "Simulation suppression objet AD"
        }
    }

    $DeletedObject = Convert-EitasAdAdminObjectItem -Object $Object
    $OuProtectionDisabled = $false
    $ContactProtectionDisabled = $false

    if ($IsOu -and $OuWasProtected) {
        Set-ADOrganizationalUnit `
            -Identity $ObjectDn `
            -ProtectedFromAccidentalDeletion $false `
            -ErrorAction Stop

        $OuProtectionDisabled = $true
    }

    if ($IsContact -and $ContactWasProtected) {
        Set-ADObject `
            -Identity $ObjectDn `
            -ProtectedFromAccidentalDeletion $false `
            -ErrorAction Stop

        $ContactProtectionDisabled = $true
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
        contact_protection_disabled = $ContactProtectionDisabled
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

    $Object = Resolve-EitasAdAdminObject -Config $Config -Identity $ObjectIdentity

    $ObjectDn = [string]$Object.DistinguishedName
    $ObjectClass = ([string]$Object.ObjectClass).Trim().ToLowerInvariant()
    $IsComputer = $ObjectClass -eq "computer"
    $IsOu = $ObjectClass -eq "organizationalunit"
    $IsContact = $ObjectClass -eq "contact"

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

        if (
            $NewName.StartsWith("-") -or
            $NewName.EndsWith("-")
        ) {
            throw "Le nom ordinateur ne peut pas commencer ou finir par un tiret"
        }

        if ($NewName -match "^[0-9]+$") {
            throw "Le nom ordinateur ne peut pas contenir uniquement des chiffres"
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

    if ($IsOu) {
        $OuCommaIndex = $ObjectDn.IndexOf(",")

        if ($OuCommaIndex -lt 1) {
            throw "DN objet invalide : $ObjectDn"
        }

        $OuParentDn = $ObjectDn.Substring($OuCommaIndex + 1)
        $SafeOuName = $NewName.Replace("\", "\5c").Replace("*", "\2a").Replace("(", "\28").Replace(")", "\29")

        $OuConflict = Get-ADOrganizationalUnit `
            -LDAPFilter "(name=$SafeOuName)" `
            -SearchBase $OuParentDn `
            -SearchScope OneLevel `
            -Properties distinguishedName `
            -ErrorAction Stop |
            Where-Object {
                [string]$_.DistinguishedName -ine $ObjectDn
            } |
            Select-Object -First 1

        if ($null -ne $OuConflict) {
            throw "OU déjà existante : $NewName dans $OuParentDn"
        }
    }

    if ($IsContact) {
        $ContactCommaIndex = $ObjectDn.IndexOf(",")

        if ($ContactCommaIndex -lt 1) {
            throw "DN objet invalide : $ObjectDn"
        }

        $ContactParentDn = $ObjectDn.Substring(
            $ContactCommaIndex + 1
        )

        $SafeContactName = $NewName.
            Replace("\", "\5c").
            Replace("*", "\2a").
            Replace("(", "\28").
            Replace(")", "\29")

        $ContactConflict = Get-ADObject `
            -LDAPFilter "(&(objectClass=contact)(name=$SafeContactName))" `
            -SearchBase $ContactParentDn `
            -SearchScope OneLevel `
            -Properties distinguishedName `
            -ErrorAction Stop |
            Where-Object {
                [string]$_.DistinguishedName -ine $ObjectDn
            } |
            Select-Object -First 1

        if ($null -ne $ContactConflict) {
            throw "Contact déjà existant : $NewName dans $ContactParentDn"
        }
    }

    if ($Mode -ne "Production") {
        return [pscustomobject]@{
            action = "rename_object"
            simulated = $true
            object_identity = $ObjectIdentity
            new_name = $NewName
            message = "Simulation renommage objet AD"
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

    $Object = Resolve-EitasAdAdminObject -Config $Config -Identity $ObjectIdentity

    Assert-EitasDnSafe -DistinguishedName $TargetParentDn -Config $Config | Out-Null

    $TargetParent = Get-ADObject `
        -Identity $TargetParentDn `
        -Properties objectClass, distinguishedName, name `
        -ErrorAction Stop

    Assert-EitasDnSafe -DistinguishedName $TargetParent.DistinguishedName -Config $Config | Out-Null

    $TargetParentClass = [string]$TargetParent.ObjectClass

    if (
        $TargetParentClass -ine "organizationalUnit" `
        -and $TargetParentClass -ine "container"
    ) {
        throw "Destination invalide : l'objet cible doit etre une OU ou un conteneur AD"
    }

    $ObjectDn = [string]$Object.DistinguishedName
    $TargetDn = [string]$TargetParent.DistinguishedName

    if ($TargetDn -ieq $ObjectDn -or $TargetDn.ToLowerInvariant().EndsWith("," + $ObjectDn.ToLowerInvariant())) {
        throw "Déplacement impossible : la destination est l’objet lui-même ou un de ses enfants"
    }

    $MoveObjectName = ([string]$Object.Name).Trim()
    $SafeMoveName = $MoveObjectName.Replace("\", "\5c").Replace("*", "\2a").Replace("(", "\28").Replace(")", "\29")

    $MoveConflict = Get-ADObject `
        -LDAPFilter "(name=$SafeMoveName)" `
        -SearchBase $TargetDn `
        -SearchScope OneLevel `
        -Properties distinguishedName `
        -ErrorAction Stop |
        Where-Object {
            [string]$_.DistinguishedName -ine $ObjectDn
        } |
        Select-Object -First 1

    if ($null -ne $MoveConflict) {
        throw "Un objet du même nom existe déjà dans la destination : $MoveObjectName"
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



function Invoke-EitasAdAdminUpdateLdapAttributesSimulation {
param(
        [object]$Config,
        [object]$Payload,
        [string]$Mode
    )

    if (
        [string]::IsNullOrWhiteSpace($Mode) -or
        $Mode.Trim() -ine "Simulation"
    ) {
        throw "La mise à jour LDAP est autorisée uniquement en Simulation"
    }

    $ExecutionPolicy = [string](
        Get-EitasObjectValue `
            -Object $Payload `
            -Names @(
                "execution_policy",
                "executionPolicy"
            )
    )

    $SimulationAuthorized = Get-EitasObjectValue `
        -Object $Payload `
        -Names @(
            "simulation_job_authorized",
            "simulationJobAuthorized"
        )

    $ProductionAuthorized = Get-EitasObjectValue `
        -Object $Payload `
        -Names @(
            "production_authorized",
            "productionAuthorized"
        )

    $ExecutionAuthorized = Get-EitasObjectValue `
        -Object $Payload `
        -Names @(
            "execution_authorized",
            "executionAuthorized"
        )

    if ($ExecutionPolicy -cne "simulation_only") {
        throw "Politique d'exécution LDAP invalide"
    }

    if ($SimulationAuthorized -ne $true) {
        throw "Autorisation de Simulation LDAP absente"
    }

    if ($ProductionAuthorized -ne $false) {
        throw "La Production LDAP doit rester interdite"
    }

    if ($ExecutionAuthorized -ne $false) {
        throw "L'écriture LDAP doit rester interdite"
    }

    $ObjectIdentity = [string](
        Get-EitasObjectValue `
            -Object $Payload `
            -Names @(
                "object_identity",
                "objectIdentity",
                "object_dn",
                "objectDn",
                "distinguished_name",
                "distinguishedName",
                "dn"
            )
    )

    $RequestedClass = [string](
        Get-EitasObjectValue `
            -Object $Payload `
            -Names @(
                "object_class",
                "objectClass"
            )
    )

    $ChangesValue = $null

    if ($Payload -is [System.Collections.IDictionary]) {
        foreach ($Name in @("changes", "Changes")) {
            if ($Payload.Contains($Name)) {
                $ChangesValue = $Payload[$Name]
                break
            }
        }
    }
    elseif ($null -ne $Payload) {
        foreach ($Name in @("changes", "Changes")) {
            if ($Payload.PSObject.Properties.Name -contains $Name) {
                $ChangesValue = $Payload.$Name
                break
            }
        }
    }

    if ($null -eq $ChangesValue) {
        throw "Liste des modifications LDAP manquante"
    }

    if ([string]::IsNullOrWhiteSpace($ObjectIdentity)) {
        throw "Identité objet LDAP manquante"
    }

    if ([string]::IsNullOrWhiteSpace($RequestedClass)) {
        throw "Classe objet LDAP manquante"
    }

    $RequestedClass = $RequestedClass.Trim().ToLowerInvariant()
    $Changes = @($ChangesValue)

    if ($Changes.Count -lt 1) {
        throw "Aucune modification LDAP fournie"
    }

    if ($Changes.Count -gt 5) {
        throw "Un job LDAP ne peut pas dépasser cinq modifications"
    }

    $AllowedAttributes = @{
        employeeType = @(
            "user"
        )
        preferredLanguage = @(
            "user"
        )
        personalTitle = @(
            "user",
            "contact"
        )
        middleName = @(
            "user",
            "contact"
        )
        comment = @(
            "user",
            "contact"
        )
        "msDS-HABSeniorityIndex" = @(
            "user"
        )
    }

    $AllowedValueTypes = @{
        employeeType = "single_text"
        preferredLanguage = "single_text"
        personalTitle = "single_text"
        middleName = "single_text"
        comment = "single_text"
        "msDS-HABSeniorityIndex" = "integer32"
    }

    $NormalizedChanges = @()
    $AttributeNames = @()

    foreach ($Change in $Changes) {
        $AttributeName = [string](
            Get-EitasObjectValue `
                -Object $Change `
                -Names @(
                    "attribute_name",
                    "attributeName"
                )
        )

        $Operation = [string](
            Get-EitasObjectValue `
                -Object $Change `
                -Names @(
                    "operation",
                    "Operation"
                )
        )

        $Value = Get-EitasObjectValue `
            -Object $Change `
            -Names @(
                "value",
                "Value"
            )

        $ValueType = [string](
            Get-EitasObjectValue `
                -Object $Change `
                -Names @(
                    "value_type",
                    "valueType"
                )
        )

        if ([string]::IsNullOrWhiteSpace($AttributeName)) {
            throw "Nom d'attribut LDAP manquant"
        }

        if (-not $AllowedAttributes.ContainsKey($AttributeName)) {
            throw "Attribut LDAP non autorisé côté agent : $AttributeName"
        }

        if (
            @($AllowedAttributes[$AttributeName]) -notcontains
            $RequestedClass
        ) {
            throw (
                "L'attribut $AttributeName n'est pas autorisé " +
                "pour la classe $RequestedClass"
            )
        }

        if ([string]::IsNullOrWhiteSpace($ValueType)) {
            $ValueType = "single_text"
        }
        else {
            $ValueType = (
                $ValueType
            ).Trim().ToLowerInvariant()
        }

        $ExpectedValueType = [string](
            $AllowedValueTypes[$AttributeName]
        )

        if ($ValueType -cne $ExpectedValueType) {
            throw (
                "Type LDAP invalide pour $AttributeName : " +
                "$ValueType, attendu $ExpectedValueType"
            )
        }

        if ($AttributeNames -contains $AttributeName) {
            throw "Attribut LDAP dupliqué : $AttributeName"
        }

        $Operation = $Operation.Trim().ToLowerInvariant()

        if (@("set", "clear") -notcontains $Operation) {
            throw "Opération LDAP non autorisée : $Operation"
        }

        if ($Operation -eq "set") {
            if ($null -eq $Value) {
                throw "Une valeur non vide est obligatoire pour set"
            }

            if ($ValueType -eq "single_text") {
                if ($Value -isnot [string]) {
                    throw (
                        "Valeur LDAP single_text invalide pour " +
                        $AttributeName
                    )
                }

                $Value = $Value.Trim()

                if (
                    [string]::IsNullOrWhiteSpace($Value)
                ) {
                    throw (
                        "Une valeur non vide est obligatoire pour set"
                    )
                }
            }
        }
        else {
            if (
                $null -ne $Value -and
                -not [string]::IsNullOrWhiteSpace(
                    [string]$Value
                )
            ) {
                throw "Aucune valeur ne doit accompagner clear"
            }

            $Value = $null
        }

        $AttributeNames += $AttributeName

        $NormalizedChanges += [pscustomobject]@{
            attribute_name = $AttributeName
            operation = $Operation
            value_type = $ValueType
            value = $Value
        }
    }

    $Object = Resolve-EitasAdAdminObject `
        -Config $Config `
        -Identity $ObjectIdentity

    $ObjectDn = ([string]$Object.DistinguishedName).Trim()
    $ResolvedClass = (
        [string]$Object.ObjectClass
    ).Trim().ToLowerInvariant()

    if ($ResolvedClass -cne $RequestedClass) {
        throw (
            "Classe objet inattendue : demandé $RequestedClass, " +
            "résolu $ResolvedClass"
        )
    }

    $CurrentObject = Get-ADObject `
        -Identity $ObjectDn `
        -Properties $AttributeNames `
        -ErrorAction Stop

    $Preview = @()

    foreach ($Change in $NormalizedChanges) {
        $AttributeName = [string]$Change.attribute_name
        $BeforeRaw = $CurrentObject.$AttributeName
        $BeforeItems = @()

        if ($null -ne $BeforeRaw) {
            $BeforeItems = @(
                $BeforeRaw |
                    ForEach-Object {
                        [string]$_
                    }
            )
        }

        $BeforeValue = $null

        if ($BeforeItems.Count -eq 1) {
            $BeforeValue = $BeforeItems[0]
        }
        elseif ($BeforeItems.Count -gt 1) {
            $BeforeValue = @($BeforeItems)
        }

        $AfterValue = $null
        $ValueType = [string]$Change.value_type

        if ([string]::IsNullOrWhiteSpace($ValueType)) {
            $ValueType = "single_text"
        }

        if ($Change.operation -eq "set") {
            switch ($ValueType) {
                "single_text" {
                    if ($Change.value -isnot [string]) {
                        throw (
                            "Valeur LDAP single_text invalide pour " +
                            $AttributeName
                        )
                    }

                    $AfterValue = $Change.value
                }

                "boolean" {
                    if ($Change.value -isnot [bool]) {
                        throw (
                            "Valeur LDAP boolean invalide pour " +
                            $AttributeName
                        )
                    }

                    $AfterValue = [bool]$Change.value
                }

                "integer32" {
                    $IsIntegerValue = (
                        $Change.value -is [byte] -or
                        $Change.value -is [sbyte] -or
                        $Change.value -is [int16] -or
                        $Change.value -is [uint16] -or
                        $Change.value -is [int32] -or
                        $Change.value -is [uint32] -or
                        $Change.value -is [int64] -or
                        $Change.value -is [uint64]
                    )

                    if (-not $IsIntegerValue) {
                        throw (
                            "Valeur LDAP integer32 invalide pour " +
                            $AttributeName
                        )
                    }

                    try {
                        $AfterValue = [Convert]::ToInt32(
                            $Change.value
                        )
                    }
                    catch {
                        throw (
                            "Valeur LDAP integer32 hors limites pour " +
                            $AttributeName
                        )
                    }
                }

                "integer64" {
                    $IsIntegerValue = (
                        $Change.value -is [byte] -or
                        $Change.value -is [sbyte] -or
                        $Change.value -is [int16] -or
                        $Change.value -is [uint16] -or
                        $Change.value -is [int32] -or
                        $Change.value -is [uint32] -or
                        $Change.value -is [int64] -or
                        $Change.value -is [uint64]
                    )

                    if (-not $IsIntegerValue) {
                        throw (
                            "Valeur LDAP integer64 invalide pour " +
                            $AttributeName
                        )
                    }

                    try {
                        $AfterValue = [Convert]::ToInt64(
                            $Change.value
                        )
                    }
                    catch {
                        throw (
                            "Valeur LDAP integer64 hors limites pour " +
                            $AttributeName
                        )
                    }
                }

                default {
                    throw (
                        "Type de valeur LDAP inconnu : " +
                        $ValueType
                    )
                }
            }
        }
        elseif ($Change.operation -eq "clear") {
            if ($null -ne $Change.value) {
                throw (
                    "Une suppression LDAP ne doit pas " +
                    "contenir de valeur"
                )
            }
        }
        else {
            throw (
                "Opération LDAP non prise en charge : " +
                [string]$Change.operation
            )
        }

        $Preview += [pscustomobject]@{
            attribute_name = $AttributeName
            operation = [string]$Change.operation
            value_type = $ValueType
            before = $BeforeValue
            after = $AfterValue
        }
    }

    return [pscustomobject]@{
        action = "update_ldap_attributes"
        simulated = $true
        mode = "Simulation"
        execution_policy = $ExecutionPolicy
        object = [string]$Object.Name
        object_type = $ResolvedClass
        object_dn = $ObjectDn
        change_count = $Preview.Count
        changes = @($Preview)
        message = (
            "Simulation LDAP calculée sans écriture " +
            "Active Directory"
        )
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

        
        "create_contact" {
            return Invoke-EitasAdAdminCreateContact `
                -Config $Config `
                -Payload $Payload `
                -Mode $Mode
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

        "set_primary_group" {
            return Invoke-EitasAdAdminSetPrimaryGroup -Config $Config -Payload $Payload -Mode $Mode
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

        "update_ldap_attributes" {
            return Invoke-EitasAdAdminUpdateLdapAttributesSimulation -Config $Config -Payload $Payload -Mode $Mode
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

