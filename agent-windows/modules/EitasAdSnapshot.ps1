function Convert-EitasSnapshotDateValue {
    param([object]$Value)

    if ($null -eq $Value) {
        return $null
    }

    try {
        $DateValue = [datetime]$Value

        return $DateValue.ToUniversalTime().ToString(
            "yyyy-MM-ddTHH:mm:ss.fffZ",
            [System.Globalization.CultureInfo]::InvariantCulture
        )
    }
    catch {
        return [string]$Value
    }
}


function Convert-EitasSnapshotFileTimeValue {
    param([object]$Value)

    if ($null -eq $Value) {
        return $null
    }

    try {
        $NumericValue = [int64]$Value

        if ($NumericValue -le 0) {
            return $null
        }

        if ($NumericValue -eq 9223372036854775807) {
            return $null
        }

        return [datetime]::FromFileTimeUtc(
            $NumericValue
        ).ToString(
            "yyyy-MM-ddTHH:mm:ss.fffZ",
            [System.Globalization.CultureInfo]::InvariantCulture
        )
    }
    catch {
        return $null
    }
}


function Get-EitasSnapshotGroupScope {
    param([object]$GroupTypeValue)

    try {
        $GroupType = [int64]$GroupTypeValue

        if (($GroupType -band 8) -ne 0) {
            return "Universal"
        }

        if (($GroupType -band 4) -ne 0) {
            return "DomainLocal"
        }

        if (($GroupType -band 2) -ne 0) {
            return "Global"
        }
    }
    catch {}

    return $null
}


function Get-EitasSnapshotGroupCategory {
    param([object]$GroupTypeValue)

    if (
        $null -eq $GroupTypeValue -or
        [string]::IsNullOrWhiteSpace(
            [string]$GroupTypeValue
        )
    ) {
        return $null
    }

    try {
        $GroupType = [int64]$GroupTypeValue

        if (($GroupType -band 2147483648) -ne 0) {
            return "Security"
        }

        return "Distribution"
    }
    catch {
        return $null
    }
}


function Get-EitasSnapshotObjectType {
    param([object]$Object)

    $ObjectClass = (
        [string]$Object.ObjectClass
    ).ToLowerInvariant()

    switch ($ObjectClass) {
        "organizationalunit" {
            return "ou"
        }

        "group" {
            return "group"
        }

        "computer" {
            return "computer"
        }

        "contact" {
            return "contact"
        }

        "user" {
            return "user"
        }

        default {
            return $ObjectClass
        }
    }
}



function Get-EitasSnapshotPrimaryGroup {
    param(
        [object]$Object,
        [string]$ObjectType,
        [string]$DomainSid,
        [hashtable]$Cache
    )

    if (
        $ObjectType -notin @(
            "user",
            "computer"
        )
    ) {
        return $null
    }

    $PrimaryGroupId = 0

    try {
        $PrimaryGroupId =
            [int64]$Object.primaryGroupID
    }
    catch {}

    if (
        $PrimaryGroupId -le 0 -or
        [string]::IsNullOrWhiteSpace(
            $DomainSid
        )
    ) {
        return $null
    }

    $CacheKey = [string]$PrimaryGroupId

    if ($Cache.ContainsKey($CacheKey)) {
        return $Cache[$CacheKey]
    }

    $PrimaryGroupSid = (
        "{0}-{1}" -f
        $DomainSid,
        $PrimaryGroupId
    )

    $Result = [pscustomobject]@{
        id = $PrimaryGroupId
        name = ""
        sam_account_name = ""
        distinguished_name = ""
        sid = $PrimaryGroupSid
    }

    try {
        $Group = Get-ADGroup `
            -Identity $PrimaryGroupSid `
            -Properties sAMAccountName `
            -ErrorAction Stop

        $Result = [pscustomobject]@{
            id = $PrimaryGroupId
            name = [string]$Group.Name
            sam_account_name = `
                [string]$Group.sAMAccountName
            distinguished_name = `
                [string]$Group.DistinguishedName
            sid = [string]$Group.SID
        }
    }
    catch {
        # La génération reste disponible si le groupe
        # principal ne peut pas être résolu.
    }

    $Cache[$CacheKey] = $Result

    return $Result
}

function Convert-EitasSnapshotByteArrayToHex {
    param([object]$Value)

    if ($null -eq $Value) {
        return ""
    }

    $Bytes = @($Value)

    if ($Bytes.Count -eq 0) {
        return ""
    }

    return (
        $Bytes |
            ForEach-Object {
                ([byte]$_).ToString("X2")
            }
    ) -join " "
}


function Convert-EitasSnapshotNullableInt32 {
    param([object]$Value)

    if (
        $null -eq $Value -or
        [string]::IsNullOrWhiteSpace(
            [string]$Value
        )
    ) {
        return $null
    }

    try {
        return [Convert]::ToInt32($Value)
    }
    catch {
        throw (
            "Valeur Integer32 Active Directory invalide"
        )
    }
}


function Convert-EitasSnapshotObject {
    param(
        [object]$Object,
        [string]$DomainSid,
        [hashtable]$PrimaryGroupCache
    )

    $Type = Get-EitasSnapshotObjectType `
        -Object $Object

    $PrimaryGroup = Get-EitasSnapshotPrimaryGroup `
        -Object $Object `
        -ObjectType $Type `
        -DomainSid $DomainSid `
        -Cache $PrimaryGroupCache

    $PrimaryGroupId = $null
    $PrimaryGroupName = ""
    $PrimaryGroupSamAccountName = ""
    $PrimaryGroupDn = ""
    $PrimaryGroupSid = ""

    if ($null -ne $PrimaryGroup) {
        $PrimaryGroupId = $PrimaryGroup.id
        $PrimaryGroupName = `
            [string]$PrimaryGroup.name
        $PrimaryGroupSamAccountName = `
            [string]$PrimaryGroup.sam_account_name
        $PrimaryGroupDn = `
            [string]$PrimaryGroup.distinguished_name
        $PrimaryGroupSid = `
            [string]$PrimaryGroup.sid
    }

    $ProtectedFromAccidentalDeletion = $null

    if (
        $Type -in @(
            "ou",
            "computer",
            "contact"
        )
    ) {
        $ProtectedFromAccidentalDeletion =
            [bool]$Object.ProtectedFromAccidentalDeletion
    }

    $Members = @(
        $Object.member |
            ForEach-Object {
                [string]$_
            }
    )

    $MemberOf = @(
        $Object.memberOf |
            ForEach-Object {
                [string]$_
            }
    )

    $UserAccountControl = 0
    $LockoutTime = 0

    try {
        $UserAccountControl = [int64]$Object.userAccountControl
    }
    catch {}

    try {
        $LockoutTime = [int64]$Object.lockoutTime
    }
    catch {}

    $Enabled = $null
    $LockedOut = $null
    $PasswordExpired = $null
    $PasswordNeverExpires = $null
    $SmartcardLogonRequired = $null
    $AccountNotDelegated = $null
    $MsTsAllowLogon = $null
    $PwdLastSetValue = 0

    try {
        $PwdLastSetValue = [int64]$Object.pwdLastSet
    }
    catch {}

    if (
        $Type -eq "user" -or
        $Type -eq "computer"
    ) {
        $Enabled = (
            ($UserAccountControl -band 2) -eq 0
        )
    }

    if ($Type -eq "user") {
        $LockedOut = (
            $LockoutTime -gt 0
        )

        $PasswordExpired = (
            $PwdLastSetValue -eq 0
        )

        $PasswordNeverExpires = (
            ($UserAccountControl -band 65536) -ne 0
        )

        $SmartcardLogonRequired = (
            ($UserAccountControl -band 262144) -ne 0
        )

        $AccountNotDelegated = (
            ($UserAccountControl -band 1048576) -ne 0
        )

        if ($null -ne $Object.msTSAllowLogon) {
            $MsTsAllowLogon = (
                [bool]$Object.msTSAllowLogon
            )
        }
    }

    $PostOfficeBoxValues = @(
        $Object.postOfficeBox |
            ForEach-Object {
                ([string]$_).Trim()
            } |
            Where-Object {
                -not [string]::IsNullOrWhiteSpace($_)
            }
    )

    $PostOfficeBoxValue = ""

    if ($PostOfficeBoxValues.Count -eq 1) {
        $PostOfficeBoxValue = (
            [string]$PostOfficeBoxValues[0]
        )
    }

    $CountryNumericCode = $null

    if (
        $null -ne $Object.countryCode -and
        -not [string]::IsNullOrWhiteSpace(
            [string]$Object.countryCode
        )
    ) {
        $CountryNumericCode = (
            [int]$Object.countryCode
        )
    }

    return [pscustomobject]@{
        type = $Type
        object_class = $Type

        name = [string]$Object.Name
        display_name = [string]$Object.displayName
        given_name = [string]$Object.givenName
        personal_title = [string]$Object.personalTitle
        initials = [string]$Object.initials
        preferred_language = [string]$Object.preferredLanguage
        uid_number = Convert-EitasSnapshotNullableInt32 `
            -Value $Object.uidNumber
        gid_number = Convert-EitasSnapshotNullableInt32 `
            -Value $Object.gidNumber
        unix_home_directory = `
            [string]$Object.unixHomeDirectory
        login_shell = [string]$Object.loginShell
        gecos = [string]$Object.gecos
        surname = [string]$Object.sn

        distinguished_name = [string]$Object.DistinguishedName
        dn = [string]$Object.DistinguishedName
        canonical_name = [string]$Object.canonicalName

        sam_account_name = [string]$Object.sAMAccountName
        user_principal_name = [string]$Object.userPrincipalName
        user_workstations = [string]$Object.userWorkstations
        logon_hours = Convert-EitasSnapshotByteArrayToHex `
            -Value $Object.logonHours
        logon_hours_utc_offset_minutes = [int](
            [System.TimeZoneInfo]::Local.BaseUtcOffset.
                TotalMinutes
        )
        direct_reports = @($Object.directReports)
        profile_path = [string]$Object.profilePath
        script_path = [string]$Object.scriptPath
        home_directory = [string]$Object.homeDirectory
        home_drive = [string]$Object.homeDrive
        ms_ts_allow_logon = $MsTsAllowLogon
        ms_ts_profile_path = [string]$Object.msTSProfilePath
        ms_ts_home_directory = [string]$Object.msTSHomeDirectory
        ms_ts_home_drive = [string]$Object.msTSHomeDrive
        ms_ts_initial_program = [string]$Object.msTSInitialProgram
        ms_ts_work_directory = [string]$Object.msTSWorkDirectory
        mail = [string]$Object.mail
        www_home_page = [string]$Object.wWWHomePage
        info = [string]$Object.info

        description = [string]$Object.description
        department = [string]$Object.department
        title = [string]$Object.title
        company = [string]$Object.company
        manager = [string]$Object.manager

        office = [string]$Object.physicalDeliveryOfficeName
        telephone_number = [string]$Object.telephoneNumber
        home_phone = [string]$Object.homePhone
        facsimile_telephone_number = [string]$Object.facsimileTelephoneNumber
        pager = [string]$Object.pager
        ip_phone = [string]$Object.ipPhone
        mobile = [string]$Object.mobile

        city = [string]$Object.l
        country = [string]$Object.co
        country_alpha2 = [string]$Object.c
        country_numeric_code = $CountryNumericCode
        state = [string]$Object.st
        postal_code = [string]$Object.postalCode
        street_address = [string]$Object.streetAddress
        post_office_box = $PostOfficeBoxValue
        post_office_boxes = @(
            $PostOfficeBoxValues
        )
        post_office_box_count = (
            [int]$PostOfficeBoxValues.Count
        )

        employee_id = [string]$Object.employeeID
        employee_number = [string]$Object.employeeNumber
        division = [string]$Object.division

        enabled = $Enabled
        locked_out = $LockedOut
        password_expired = $PasswordExpired
        password_never_expires = $PasswordNeverExpires
        smartcard_logon_required = $SmartcardLogonRequired
        account_not_delegated = $AccountNotDelegated

        password_last_set = Convert-EitasSnapshotFileTimeValue `
            -Value $Object.pwdLastSet

        last_logon = Convert-EitasSnapshotFileTimeValue `
            -Value $Object.lastLogonTimestamp

        last_bad_password_attempt = Convert-EitasSnapshotFileTimeValue `
            -Value $Object.badPasswordTime

        account_expires = Convert-EitasSnapshotFileTimeValue `
            -Value $Object.accountExpires

        bad_logon_count = $Object.badPwdCount

        group_scope = Get-EitasSnapshotGroupScope `
            -GroupTypeValue $Object.groupType

        group_category = Get-EitasSnapshotGroupCategory `
            -GroupTypeValue $Object.groupType

        members = $Members
        member_count = $Members.Count
        member_of = $MemberOf

        primary_group_id = $PrimaryGroupId
        primary_group_name = $PrimaryGroupName
        primary_group_sam_account_name = `
            $PrimaryGroupSamAccountName
        primary_group_dn = $PrimaryGroupDn
        primary_group_sid = $PrimaryGroupSid

        dns_host_name = [string]$Object.dNSHostName
        operating_system = [string]$Object.operatingSystem
        operating_system_version = [string]$Object.operatingSystemVersion
        operating_system_service_pack = [string]$Object.operatingSystemServicePack
        location = [string]$Object.location
        managed_by = [string]$Object.managedBy
        com_plus_partition_set_dn = [string]$Object.'msCOM-UserPartitionSetLink'
        protected_from_accidental_deletion = $ProtectedFromAccidentalDeletion

        created_at = Convert-EitasSnapshotDateValue `
            -Value $Object.whenCreated

        updated_at = Convert-EitasSnapshotDateValue `
            -Value $Object.whenChanged

        usn_changed = [int64]$Object.uSNChanged
        usn_created = [int64]$Object.uSNCreated

        object_guid = [string]$Object.ObjectGUID
        sid = [string]$Object.objectSid
    }
}


function New-EitasAdSnapshot {
    param([object]$Config)

    Import-EitasActiveDirectoryModule |
        Out-Null

    $BaseDn = Get-EitasAllowedBaseDn `
        -Config $Config

    Assert-EitasDnSafe `
        -DistinguishedName $BaseDn `
        -Config $Config |
        Out-Null

    $Domain = Get-ADDomain `
        -ErrorAction Stop

    $DomainSid = [string]$Domain.DomainSID.Value

    if (
        [string]::IsNullOrWhiteSpace(
            $DomainSid
        )
    ) {
        $DomainSid =
            [string]$Domain.DomainSID
    }

    $PrimaryGroupCache = @{}

    $Properties = @(
        "description",
        "displayName",
        "givenName",
        "personalTitle",
        "initials",
        "preferredLanguage",
        "uidNumber",
        "gidNumber",
        "unixHomeDirectory",
        "loginShell",
        "gecos",
        "sn",
        "sAMAccountName",
        "userPrincipalName",
        "userWorkstations",
        "logonHours",
        "directReports",
        "profilePath",
        "scriptPath",
        "homeDirectory",
        "homeDrive",
        "msTSAllowLogon",
        "msTSProfilePath",
        "msTSHomeDirectory",
        "msTSHomeDrive",
        "msTSInitialProgram",
        "msTSWorkDirectory",
        "mail",
        "wWWHomePage",
        "info",
        "userAccountControl",
        "pwdLastSet",
        "lastLogonTimestamp",
        "badPasswordTime",
        "accountExpires",
        "lockoutTime",
        "badPwdCount",
        "department",
        "title",
        "company",
        "manager",
        "physicalDeliveryOfficeName",
        "telephoneNumber",
        "homePhone",
        "facsimileTelephoneNumber",
        "pager",
        "ipPhone",
        "mobile",
        "l",
        "c",
        "co",
        "countryCode",
        "st",
        "postalCode",
        "streetAddress",
        "postOfficeBox",
        "employeeID",
        "employeeNumber",
        "division",
        "member",
        "memberOf",
        "primaryGroupID",
        "groupType",
        "canonicalName",
        "whenCreated",
        "whenChanged",
        "uSNChanged",
        "uSNCreated",
        "dNSHostName",
        "operatingSystem",
        "operatingSystemVersion",
        "operatingSystemServicePack",
        "location",
        "managedBy",
        "msCOM-UserPartitionSetLink",
        "ProtectedFromAccidentalDeletion",
        "objectGUID",
        "objectSid"
    )

    $LdapFilter = "(|(objectClass=organizationalUnit)(objectClass=group)(&(objectCategory=person)(objectClass=user))(objectClass=computer)(objectClass=contact))"

    $Watch = [System.Diagnostics.Stopwatch]::StartNew()

    $Objects = @(
        Get-ADObject `
            -LDAPFilter $LdapFilter `
            -SearchBase $BaseDn `
            -SearchScope Subtree `
            -Properties $Properties `
            -ErrorAction Stop
    )

    $Items = @(
        foreach ($Object in $Objects) {
            Convert-EitasSnapshotObject `
                -Object $Object `
                -DomainSid $DomainSid `
                -PrimaryGroupCache $PrimaryGroupCache
        }
    )

    $Items = @(
        $Items |
            Sort-Object `
                @{Expression={$_.type}},
                @{Expression={$_.name}}
    )

    $Watch.Stop()

    $GeneratedAt = (
        Get-Date
    ).ToUniversalTime().ToString(
        "yyyy-MM-ddTHH:mm:ss.fffZ",
        [System.Globalization.CultureInfo]::InvariantCulture
    )

    return [pscustomobject]@{
        version = $GeneratedAt
        generated_at = $GeneratedAt
        domain = [string]$Domain.DNSRoot
        base_dn = [string]$BaseDn
        controller = [string]$env:COMPUTERNAME
        count = $Items.Count
        build_milliseconds = [Math]::Round(
            $Watch.Elapsed.TotalMilliseconds,
            3
        )
        items = $Items
    }
}


function Convert-EitasDomainCatalogObject {
    param(
        [object]$Object,
        [string]$DomainSid,
        [hashtable]$PrimaryGroupCache
    )

    $Type = Get-EitasSnapshotObjectType `
        -Object $Object

    if (
        $Type -notin @(
            "user",
            "group",
            "computer"
        )
    ) {
        return $null
    }

    $PrimaryGroup = Get-EitasSnapshotPrimaryGroup `
        -Object $Object `
        -ObjectType $Type `
        -DomainSid $DomainSid `
        -Cache $PrimaryGroupCache

    $PrimaryGroupId = $null
    $PrimaryGroupName = ""
    $PrimaryGroupSamAccountName = ""
    $PrimaryGroupDn = ""
    $PrimaryGroupSid = ""

    if ($null -ne $PrimaryGroup) {
        $PrimaryGroupId = $PrimaryGroup.id
        $PrimaryGroupName = `
            [string]$PrimaryGroup.name
        $PrimaryGroupSamAccountName = `
            [string]$PrimaryGroup.sam_account_name
        $PrimaryGroupDn = `
            [string]$PrimaryGroup.distinguished_name
        $PrimaryGroupSid = `
            [string]$PrimaryGroup.sid
    }

    $UserAccountControl = 0

    try {
        $UserAccountControl = [int64]$Object.userAccountControl
    }
    catch {}

    $Enabled = $null
    $SmartcardLogonRequired = $null
    $AccountNotDelegated = $null
    $MsTsAllowLogon = $null

    if (
        $Type -eq "user" -or
        $Type -eq "computer"
    ) {
        $Enabled = (
            ($UserAccountControl -band 2) -eq 0
        )
    }

    if ($Type -eq "user") {
        $SmartcardLogonRequired = (
            ($UserAccountControl -band 262144) -ne 0
        )

        $AccountNotDelegated = (
            ($UserAccountControl -band 1048576) -ne 0
        )

        if ($null -ne $Object.msTSAllowLogon) {
            $MsTsAllowLogon = (
                [bool]$Object.msTSAllowLogon
            )
        }
    }

    $ObjectName = [string]$Object.Name
    $SamAccountName = [string]$Object.sAMAccountName
    $DisplayName = [string]$Object.displayName

    if (
        $Type -eq "computer" -and
        (
            [string]::IsNullOrWhiteSpace($DisplayName) -or
            $DisplayName -ieq $SamAccountName
        )
    ) {
        $DisplayName = $ObjectName
    }

    $GroupScope = $null
    $GroupCategory = $null

    if ($Type -eq "group") {
        $GroupScope = Get-EitasSnapshotGroupScope `
            -GroupTypeValue $Object.groupType

        $GroupCategory = Get-EitasSnapshotGroupCategory `
            -GroupTypeValue $Object.groupType
    }

    $ProtectedFromAccidentalDeletion = $null

    if ($Type -eq "computer") {
        $ProtectedFromAccidentalDeletion =
            [bool]$Object.ProtectedFromAccidentalDeletion
    }

    return [pscustomobject]@{
        type = $Type
        object_class = $Type

        name = $ObjectName
        display_name = $DisplayName
        given_name = [string]$Object.givenName
        personal_title = [string]$Object.personalTitle
        initials = [string]$Object.initials
        preferred_language = [string]$Object.preferredLanguage
        uid_number = Convert-EitasSnapshotNullableInt32 `
            -Value $Object.uidNumber
        gid_number = Convert-EitasSnapshotNullableInt32 `
            -Value $Object.gidNumber
        unix_home_directory = `
            [string]$Object.unixHomeDirectory
        login_shell = [string]$Object.loginShell
        gecos = [string]$Object.gecos
        surname = [string]$Object.sn

        distinguished_name = [string]$Object.DistinguishedName
        dn = [string]$Object.DistinguishedName
        canonical_name = [string]$Object.canonicalName

        sam_account_name = $SamAccountName
        user_principal_name = [string]$Object.userPrincipalName
        user_workstations = [string]$Object.userWorkstations
        logon_hours = Convert-EitasSnapshotByteArrayToHex `
            -Value $Object.logonHours
        logon_hours_utc_offset_minutes = [int](
            [System.TimeZoneInfo]::Local.BaseUtcOffset.
                TotalMinutes
        )
        direct_reports = @($Object.directReports)
        account_expires = Convert-EitasSnapshotFileTimeValue `
            -Value $Object.accountExpires
        profile_path = [string]$Object.profilePath
        script_path = [string]$Object.scriptPath
        home_directory = [string]$Object.homeDirectory
        home_drive = [string]$Object.homeDrive
        ms_ts_allow_logon = $MsTsAllowLogon
        ms_ts_profile_path = [string]$Object.msTSProfilePath
        ms_ts_home_directory = [string]$Object.msTSHomeDirectory
        ms_ts_home_drive = [string]$Object.msTSHomeDrive
        ms_ts_initial_program = [string]$Object.msTSInitialProgram
        ms_ts_work_directory = [string]$Object.msTSWorkDirectory
        mail = [string]$Object.mail
        info = [string]$Object.info

        description = [string]$Object.description
        department = [string]$Object.department
        title = [string]$Object.title
        company = [string]$Object.company
        manager = [string]$Object.manager

        enabled = $Enabled
        smartcard_logon_required = $SmartcardLogonRequired
        account_not_delegated = $AccountNotDelegated

        group_scope = $GroupScope
        group_category = $GroupCategory

        dns_host_name = [string]$Object.dNSHostName
        operating_system = [string]$Object.operatingSystem
        operating_system_version = [string]$Object.operatingSystemVersion
        operating_system_service_pack = [string]$Object.operatingSystemServicePack

        location = [string]$Object.location
        managed_by = [string]$Object.managedBy
        protected_from_accidental_deletion = `
            $ProtectedFromAccidentalDeletion

        last_logon = Convert-EitasSnapshotFileTimeValue `
            -Value $Object.lastLogonTimestamp

        created_at = Convert-EitasSnapshotDateValue `
            -Value $Object.whenCreated

        updated_at = Convert-EitasSnapshotDateValue `
            -Value $Object.whenChanged

        object_guid = [string]$Object.ObjectGUID
        sid = [string]$Object.objectSid

        # Le catalogue ne collecte pas l’attribut member.
        # Une liste vide signifierait à tort que le groupe est vide.
        members = $null
        member_count = $null
        member_of = @($Object.memberOf)

        primary_group_id = $PrimaryGroupId
        primary_group_name = $PrimaryGroupName
        primary_group_sam_account_name = `
            $PrimaryGroupSamAccountName
        primary_group_dn = $PrimaryGroupDn
        primary_group_sid = $PrimaryGroupSid
    }
}


function New-EitasAdDomainCatalog {
    param([object]$Config)

    Import-EitasActiveDirectoryModule |
        Out-Null

    $BaseDn = Get-EitasAdDomainDn `
        -Config $Config

    Assert-EitasDnSafe `
        -DistinguishedName $BaseDn `
        -Config $Config `
        -AllowDomainRoot |
        Out-Null

    $Domain = Get-ADDomain `
        -ErrorAction Stop

    $DomainSid = [string]$Domain.DomainSID.Value

    if (
        [string]::IsNullOrWhiteSpace(
            $DomainSid
        )
    ) {
        $DomainSid =
            [string]$Domain.DomainSID
    }

    $PrimaryGroupCache = @{}

    $Properties = @(
        "description",
        "displayName",
        "givenName",
        "personalTitle",
        "initials",
        "preferredLanguage",
        "uidNumber",
        "gidNumber",
        "unixHomeDirectory",
        "loginShell",
        "gecos",
        "sn",
        "sAMAccountName",
        "userPrincipalName",
        "accountExpires",
        "userWorkstations",
        "logonHours",
        "directReports",
        "profilePath",
        "scriptPath",
        "homeDirectory",
        "homeDrive",
        "msTSAllowLogon",
        "msTSProfilePath",
        "msTSHomeDirectory",
        "msTSHomeDrive",
        "msTSInitialProgram",
        "msTSWorkDirectory",
        "mail",
        "info",
        "userAccountControl",
        "lastLogonTimestamp",
        "department",
        "title",
        "company",
        "manager",
        "groupType",
        "canonicalName",
        "whenCreated",
        "whenChanged",
        "dNSHostName",
        "operatingSystem",
        "operatingSystemVersion",
        "operatingSystemServicePack",
        "location",
        "managedBy",
        "ProtectedFromAccidentalDeletion",
        "memberOf",
        "primaryGroupID",
        "objectGUID",
        "objectSid"
    )

    $LdapFilter = (
        "(|" +
        "(&(objectCategory=person)(objectClass=user))" +
        "(objectClass=group)" +
        "(&(objectCategory=computer)(objectClass=computer))" +
        ")"
    )

    $Watch = (
        [System.Diagnostics.Stopwatch]::StartNew()
    )

    $Objects = @(
        Get-ADObject `
            -LDAPFilter $LdapFilter `
            -SearchBase $BaseDn `
            -SearchScope Subtree `
            -Properties $Properties `
            -ErrorAction Stop
    )

    $Items = @(
        foreach ($Object in $Objects) {
            $Item = Convert-EitasDomainCatalogObject `
                -Object $Object `
                -DomainSid $DomainSid `
                -PrimaryGroupCache $PrimaryGroupCache

            if ($null -ne $Item) {
                $Item
            }
        }
    )

    $Items = @(
        $Items |
            Sort-Object `
                @{Expression={$_.type}},
                @{Expression={$_.name}}
    )

    $Watch.Stop()

    $GeneratedAt = (
        Get-Date
    ).ToUniversalTime().ToString(
        "yyyy-MM-ddTHH:mm:ss.fffZ",
        [System.Globalization.CultureInfo]::InvariantCulture
    )

    return [pscustomobject]@{
        version = $GeneratedAt
        generated_at = $GeneratedAt
        domain = [string]$Domain.DNSRoot
        base_dn = [string]$BaseDn
        controller = [string]$env:COMPUTERNAME
        count = $Items.Count

        build_milliseconds = [Math]::Round(
            $Watch.Elapsed.TotalMilliseconds,
            3
        )

        items = $Items
    }
}


function Publish-EitasAdDomainCatalog {
    param([object]$Config)

    $Catalog = New-EitasAdDomainCatalog `
        -Config $Config

    $Response = Invoke-EitasApiRequest `
        -Method "POST" `
        -Path "/api/agent/ad-domain-catalog" `
        -Body $Catalog `
        -Config $Config

    return [pscustomobject]@{
        response = $Response
        count = $Catalog.count
        generated_at = $Catalog.generated_at
        build_milliseconds = $Catalog.build_milliseconds
    }
}


function Publish-EitasAdSnapshot {
    param([object]$Config)

    $Snapshot = New-EitasAdSnapshot `
        -Config $Config

    $Response = Invoke-EitasApiRequest `
        -Method "POST" `
        -Path "/api/agent/ad-snapshot" `
        -Body $Snapshot `
        -Config $Config

    return [pscustomobject]@{
        response = $Response
        count = $Snapshot.count
        generated_at = $Snapshot.generated_at
        build_milliseconds = $Snapshot.build_milliseconds
    }
}
