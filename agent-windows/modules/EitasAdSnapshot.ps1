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


function Convert-EitasSnapshotObject {
    param([object]$Object)

    $Type = Get-EitasSnapshotObjectType `
        -Object $Object

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
    }

    return [pscustomobject]@{
        type = $Type
        object_class = $Type

        name = [string]$Object.Name
        display_name = [string]$Object.displayName

        distinguished_name = [string]$Object.DistinguishedName
        dn = [string]$Object.DistinguishedName
        canonical_name = [string]$Object.canonicalName

        sam_account_name = [string]$Object.sAMAccountName
        user_principal_name = [string]$Object.userPrincipalName
        mail = [string]$Object.mail

        description = [string]$Object.description
        department = [string]$Object.department
        title = [string]$Object.title
        company = [string]$Object.company
        manager = [string]$Object.manager

        office = [string]$Object.physicalDeliveryOfficeName
        telephone_number = [string]$Object.telephoneNumber
        mobile = [string]$Object.mobile

        city = [string]$Object.l
        country = [string]$Object.co
        state = [string]$Object.st
        postal_code = [string]$Object.postalCode
        street_address = [string]$Object.streetAddress

        employee_id = [string]$Object.employeeID
        employee_number = [string]$Object.employeeNumber
        division = [string]$Object.division

        enabled = $Enabled
        locked_out = $LockedOut
        password_expired = $PasswordExpired
        password_never_expires = $PasswordNeverExpires

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

        dns_host_name = [string]$Object.dNSHostName
        operating_system = [string]$Object.operatingSystem
        operating_system_version = [string]$Object.operatingSystemVersion
        operating_system_service_pack = [string]$Object.operatingSystemServicePack
        location = [string]$Object.location
        managed_by = [string]$Object.managedBy

        created_at = Convert-EitasSnapshotDateValue `
            -Value $Object.whenCreated

        updated_at = Convert-EitasSnapshotDateValue `
            -Value $Object.whenChanged

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

    $Properties = @(
        "description",
        "displayName",
        "sAMAccountName",
        "userPrincipalName",
        "mail",
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
        "mobile",
        "l",
        "co",
        "st",
        "postalCode",
        "streetAddress",
        "employeeID",
        "employeeNumber",
        "division",
        "member",
        "memberOf",
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
                -Object $Object
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
