function Import-EitasActiveDirectoryModule {
    try {
        Import-Module ActiveDirectory -ErrorAction Stop
        return $true
    }
    catch {
        throw "Module ActiveDirectory indisponible : $($_.Exception.Message)"
    }
}

function Get-EitasAdDomainInfo {
    Import-EitasActiveDirectoryModule | Out-Null

    try {
        return Get-ADDomain -ErrorAction Stop
    }
    catch {
        throw "Domaine AD non joignable : $($_.Exception.Message)"
    }
}

function Get-EitasAdDomainDn {
    param([object]$Config)

    if ($null -ne $Config) {
        if ($Config.DomainDn) { return [string]$Config.DomainDn }
        if ($Config.DomainDN) { return [string]$Config.DomainDN }
        if ($Config.BaseDn) { return [string]$Config.BaseDn }
        if ($Config.BaseDN) { return [string]$Config.BaseDN }
    }

    $Domain = Get-EitasAdDomainInfo
    return [string]$Domain.DistinguishedName
}

function Get-EitasAllowedBaseDn {
    param([object]$Config)

    if ($null -ne $Config) {
        if ($Config.AllowedBaseDn) { return [string]$Config.AllowedBaseDn }
        if ($Config.AllowedBaseDN) { return [string]$Config.AllowedBaseDN }
        if ($Config.EitasBaseDn) { return [string]$Config.EitasBaseDn }
        if ($Config.EitasBaseDN) { return [string]$Config.EitasBaseDN }
        if ($Config.RootOuDn) { return [string]$Config.RootOuDn }
        if ($Config.RootOUDN) { return [string]$Config.RootOUDN }
        if ($Config.EitasOuDn) { return [string]$Config.EitasOuDn }
        if ($Config.EitasOUDN) { return [string]$Config.EitasOUDN }
    }

    $DomainDn = Get-EitasAdDomainDn -Config $Config
    return "OU=EITAS,$DomainDn"
}

function Test-EitasDnSafe {
    param(
        [string]$DistinguishedName,
        [object]$Config,
        [switch]$AllowDomainRoot
    )

    if ([string]::IsNullOrWhiteSpace($DistinguishedName)) {
        return $false
    }

    $Dn = $DistinguishedName.Trim()
    $AllowedBaseDn = (Get-EitasAllowedBaseDn -Config $Config).Trim()
    $DomainDn = (Get-EitasAdDomainDn -Config $Config).Trim()

    if ($AllowDomainRoot -and ($Dn -ieq $DomainDn)) {
        return $true
    }

    if ($Dn -ieq $AllowedBaseDn) {
        return $true
    }

    if ($Dn.ToLower().EndsWith("," + $AllowedBaseDn.ToLower())) {
        return $true
    }

    return $false
}

function Assert-EitasDnSafe {
    param(
        [string]$DistinguishedName,
        [object]$Config,
        [switch]$AllowDomainRoot
    )

    if (-not (Test-EitasDnSafe -DistinguishedName $DistinguishedName -Config $Config -AllowDomainRoot:$AllowDomainRoot)) {
        throw "DN hors périmètre EITAS : $DistinguishedName"
    }

    return $true
}

function Escape-EitasLdapFilterValue {
    param([string]$Value)

    if ($null -eq $Value) {
        return ""
    }

    return ([string]$Value).
        Replace("\", "\5c").
        Replace("*", "\2a").
        Replace("(", "\28").
        Replace(")", "\29").
        Replace([string][char]0, "\00")
}

function Test-EitasAdObjectExists {
    param(
        [string]$Identity,
        [string]$SearchBase,
        [string]$ObjectClass = "*"
    )

    Import-EitasActiveDirectoryModule | Out-Null

    if ([string]::IsNullOrWhiteSpace($Identity)) {
        return $false
    }

    $Escaped = Escape-EitasLdapFilterValue -Value $Identity

    if ($ObjectClass -eq "group") {
        $Filter = "(|(cn=$Escaped)(sAMAccountName=$Escaped))"
    }
    elseif ($ObjectClass -eq "organizationalUnit") {
        $Filter = "(&(objectClass=organizationalUnit)(ou=$Escaped))"
    }
    elseif ($ObjectClass -eq "user") {
        $Filter = "(|(sAMAccountName=$Escaped)(userPrincipalName=$Escaped)(cn=$Escaped))"
    }
    else {
        $Filter = "(|(cn=$Escaped)(sAMAccountName=$Escaped)(ou=$Escaped))"
    }

    try {
        $Params = @{
            LDAPFilter = $Filter
            ErrorAction = "Stop"
            ResultSetSize = 1
        }

        if (-not [string]::IsNullOrWhiteSpace($SearchBase)) {
            $Params.SearchBase = $SearchBase
        }

        $Object = Get-ADObject @Params
        return ($null -ne $Object)
    }
    catch {
        return $false
    }
}

function Test-EitasProductionAdPreflight {
    param([object]$Config)

    Import-EitasActiveDirectoryModule | Out-Null

    $Domain = Get-EitasAdDomainInfo
    $DomainDn = Get-EitasAdDomainDn -Config $Config
    $AllowedBaseDn = Get-EitasAllowedBaseDn -Config $Config

    $BaseExists = $false

    try {
        $BaseObject = Get-ADObject -Identity $AllowedBaseDn -ErrorAction Stop
        $BaseExists = ($null -ne $BaseObject)
    }
    catch {
        $BaseExists = $false
    }

    return [pscustomobject]@{
        success = $BaseExists
        computer = $env:COMPUTERNAME
        domain = $Domain.DNSRoot
        domainDn = $DomainDn
        allowedBaseDn = $AllowedBaseDn
        allowedBaseExists = $BaseExists
        message = if ($BaseExists) { "Preflight AD valide" } else { "Base EITAS introuvable : $AllowedBaseDn" }
    }
}
