param(
    [string]$Name = "MCP_MageFireball",
    [double]$PosX = 0,
    [double]$PosY = 1,
    [double]$PosZ = 0,
    [switch]$PlayOnCreate = $true
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$serverRoot = Join-Path $repoRoot "Server"
$pythonExe = Join-Path $serverRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $pythonExe)) {
    throw "Python executable not found at '$pythonExe'. Create the server venv first."
}

function Invoke-UnityMcp {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments,
        [switch]$AllowFailure
    )

    Write-Host "> $($Arguments -join ' ')" -ForegroundColor DarkGray
    & $pythonExe -m cli.main @Arguments
    $exitCode = $LASTEXITCODE

    if (-not $AllowFailure -and $exitCode -ne 0) {
        throw "unity-mcp command failed with exit code ${exitCode}: $($Arguments -join ' ')"
    }
}

function New-BatchEntry {
    param(
        [Parameter(Mandatory = $true)][string]$Tool,
        [Parameter(Mandatory = $true)][hashtable]$Params
    )
    return @{ tool = $Tool; params = $Params }
}

$batchEntries = @(
    (New-BatchEntry -Tool "manage_gameobject" -Params @{
        action = "create"
        name = $Name
        position = @($PosX, $PosY, $PosZ)
    }),
    (New-BatchEntry -Tool "manage_vfx" -Params @{
        action = "particle_create"
        target = $Name
    }),
    (New-BatchEntry -Tool "manage_vfx" -Params @{
        action = "particle_set_main"
        target = $Name
        properties = @{
            duration = 1.8
            looping = $true
            startLifetime = 0.45
            startSpeed = 1.3
            startSize = 0.22
            startColor = @(1.0, 0.48, 0.1, 1.0)
            gravityModifier = -0.02
            maxParticles = 900
            simulationSpace = "World"
            playOnAwake = $false
        }
    }),
    (New-BatchEntry -Tool "manage_material" -Params @{
        action = "assign_material_to_renderer"
        materialPath = "Assets/MCPToolSmokeTests/Live_20260306_003519/Materials/SmokeMat.mat"
        target = $Name
        mode = "shared"
    }),
    (New-BatchEntry -Tool "manage_vfx" -Params @{
        action = "particle_set_emission"
        target = $Name
        properties = @{
            rateOverTime = 170
            rateOverDistance = 0
        }
    }),
    (New-BatchEntry -Tool "manage_vfx" -Params @{
        action = "particle_set_shape"
        target = $Name
        properties = @{
            shapeType = "Cone"
            radius = 0.08
            angle = 18
            arc = 360
        }
    }),
    (New-BatchEntry -Tool "manage_vfx" -Params @{
        action = "particle_set_noise"
        target = $Name
        properties = @{
            strength = 0.55
            frequency = 0.7
            scrollSpeed = 0.9
            damping = $true
            octaveCount = 2
        }
    }),
    (New-BatchEntry -Tool "manage_vfx" -Params @{
        action = "particle_set_color_over_lifetime"
        target = $Name
        properties = @{
            gradient = @{
                colorKeys = @(
                    @{ color = @(1.0, 0.95, 0.35, 1.0); time = 0.0 },
                    @{ color = @(1.0, 0.38, 0.06, 1.0); time = 0.55 },
                    @{ color = @(0.22, 0.02, 0.0, 1.0); time = 1.0 }
                )
                alphaKeys = @(
                    @{ alpha = 0.95; time = 0.0 },
                    @{ alpha = 0.62; time = 0.65 },
                    @{ alpha = 0.0; time = 1.0 }
                )
            }
        }
    }),
    (New-BatchEntry -Tool "manage_vfx" -Params @{
        action = "particle_set_size_over_lifetime"
        target = $Name
        properties = @{
            enabled = $true
            size = @{
                mode = "curve"
                keys = @(
                    @{ time = 0.0; value = 0.15 },
                    @{ time = 0.35; value = 1.0 },
                    @{ time = 1.0; value = 0.0 }
                )
            }
        }
    }),
    (New-BatchEntry -Tool "manage_vfx" -Params @{
        action = "particle_set_renderer"
        target = $Name
        properties = @{
            renderMode = "Stretch"
            velocityScale = 0.22
            lengthScale = 0.5
            cameraVelocityScale = 0.05
            maxParticleSize = 0.2
            minParticleSize = 0.0
        }
    }),
    (New-BatchEntry -Tool "manage_vfx" -Params @{
        action = "particle_set_velocity_over_lifetime"
        target = $Name
        properties = @{
            x = 0.0
            y = 0.2
            z = 3.4
            space = "Local"
        }
    })
)

if ($PlayOnCreate) {
    $batchEntries += New-BatchEntry -Tool "manage_vfx" -Params @{
        action = "particle_play"
        target = $Name
    }
}

$batchFile = Join-Path $env:TEMP "mcp-fireball-$([guid]::NewGuid().ToString('N')).json"
try {
    $json = $batchEntries | ConvertTo-Json -Depth 12
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($batchFile, $json, $utf8NoBom)
    Invoke-UnityMcp -Arguments @("batch", "run", $batchFile)
}
finally {
    if (Test-Path $batchFile) {
        Remove-Item $batchFile -Force -ErrorAction SilentlyContinue
    }
}

Write-Host "Mage fireball VFX setup complete on '$Name'." -ForegroundColor Green
Write-Host "Tip: Duplicate this object and vary startColor/startSize/rateOverTime for enemy tiers." -ForegroundColor Yellow
