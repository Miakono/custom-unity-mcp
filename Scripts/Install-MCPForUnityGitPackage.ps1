param(
    [Parameter(Mandatory = $true)]
    [string]$UnityProjectPath,

    [Parameter(Mandatory = $true)]
    [string]$GitUrl,

    [string]$GitRef = "main",

    [string]$PackageName = "com.customgamedev.unity-mcp",

    [string]$PackageSubdirectory = "MCPForUnity"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function ConvertTo-PlainObject {
    param(
        [Parameter(Mandatory = $true)]
        $InputObject
    )

    if ($null -eq $InputObject) {
        return $null
    }

    if (
        $InputObject -is [string] -or
        $InputObject -is [int] -or
        $InputObject -is [long] -or
        $InputObject -is [double] -or
        $InputObject -is [decimal] -or
        $InputObject -is [bool]
    ) {
        return $InputObject
    }

    if ($InputObject -is [System.Collections.IDictionary]) {
        $result = @{}
        foreach ($key in $InputObject.Keys) {
            $result[$key] = ConvertTo-PlainObject -InputObject $InputObject[$key]
        }
        return $result
    }

    if ($InputObject -is [System.Collections.IEnumerable]) {
        $items = New-Object System.Collections.ArrayList
        foreach ($item in $InputObject) {
            [void]$items.Add((ConvertTo-PlainObject -InputObject $item))
        }
        return ,$items.ToArray()
    }

    $properties = @()
    if ($null -ne $InputObject.PSObject) {
        $properties = @($InputObject.PSObject.Properties)
    }
    if ($properties.Count -gt 0) {
        $result = @{}
        foreach ($property in $properties) {
            $result[$property.Name] = ConvertTo-PlainObject -InputObject $property.Value
        }
        return $result
    }

    return $InputObject
}

function Resolve-ManifestPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ProjectPath
    )

    $manifestPath = Join-Path $ProjectPath "Packages\manifest.json"
    if (-not (Test-Path $manifestPath)) {
        throw "Could not find Unity manifest at '$manifestPath'."
    }

    return $manifestPath
}

function Normalize-GitDependency {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepositoryUrl,

        [Parameter(Mandatory = $true)]
        [string]$Subdirectory,

        [Parameter(Mandatory = $true)]
        [string]$Ref
    )

    $trimmedUrl = $RepositoryUrl.Trim()
    if ([string]::IsNullOrWhiteSpace($trimmedUrl)) {
        throw "GitUrl must not be empty."
    }

    $normalizedSubdirectory = $Subdirectory.Trim().TrimStart("/")
    if ([string]::IsNullOrWhiteSpace($normalizedSubdirectory)) {
        throw "PackageSubdirectory must not be empty."
    }

    $baseUrl = $trimmedUrl
    if ($baseUrl.Contains("?")) {
        $baseUrl = $baseUrl.Split("?")[0]
    }
    if ($baseUrl.Contains("#")) {
        $baseUrl = $baseUrl.Split("#")[0]
    }

    if (-not $baseUrl.EndsWith(".git")) {
        $baseUrl = "$baseUrl.git"
    }

    $suffix = "?path=/$normalizedSubdirectory"
    if (-not [string]::IsNullOrWhiteSpace($Ref)) {
        $suffix = "$suffix#$Ref"
    }

    return "$baseUrl$suffix"
}

$manifestPath = Resolve-ManifestPath -ProjectPath $UnityProjectPath
$manifestObject = ConvertTo-PlainObject -InputObject (Get-Content $manifestPath -Raw | ConvertFrom-Json)

if (-not $manifestObject.ContainsKey("dependencies") -or $null -eq $manifestObject["dependencies"]) {
    $manifestObject["dependencies"] = @{}
}

$dependencyValue = Normalize-GitDependency -RepositoryUrl $GitUrl -Subdirectory $PackageSubdirectory -Ref $GitRef
$manifestObject["dependencies"][$PackageName] = $dependencyValue

$manifestJson = $manifestObject | ConvertTo-Json -Depth 100
[System.IO.File]::WriteAllText($manifestPath, $manifestJson + [Environment]::NewLine, [System.Text.Encoding]::UTF8)

Write-Host "Updated $manifestPath"
Write-Host "Added package:"
Write-Host "  $PackageName = $dependencyValue"
