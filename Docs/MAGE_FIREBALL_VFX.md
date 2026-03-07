# Mage Fireball VFX (Live Test)

Status note:

This is a supporting task-specific operational note for the mage fireball live VFX workflow.

Use this file for the fireball setup script and troubleshooting only.
Do not treat it as a general project roadmap or validation status document.

Use this to create a mage-style fireball effect (glow + flame + turbulence) in a connected Unity editor.

The script now applies a non-square-friendly preset:

- `SmokeMat` assignment to the fireball renderer
- `renderMode = Stretch` for elongated/flame-like particles
- smaller particle size + size-over-lifetime shaping
- warm glow tint and velocity-over-lifetime motion

## Prerequisites

- Unity editor is running and connected to MCP.
- Server venv exists at `Server/.venv`.

## Run

From repository root:

```powershell
./Scripts/Create-MageFireballVfx.ps1
```

Optional custom spawn point and name:

```powershell
./Scripts/Create-MageFireballVfx.ps1 -Name "Mage_Fireball_Elite" -PosX 0 -PosY 1.2 -PosZ 2.5
```

## What it configures

- Creates/reuses a GameObject.
- Adds a ParticleSystem if missing.
- Sets:
  - main module (lifetime/speed/size/color/gravity/max particles)
  - emission rate
  - cone shape
  - noise turbulence
  - color-over-lifetime gradient for glow fade
  - velocity-over-lifetime for projectile feel
- Plays the effect immediately by default.

## Notes

- If `gameobject create` reports "already exists", the script continues and reconfigures the existing object.
- You can disable auto-play with:

```powershell
./Scripts/Create-MageFireballVfx.ps1 -PlayOnCreate:$false
```

## Troubleshooting

### "Everything is square"

- Make sure you selected `MCP_MageFireball_Test`, not `MCP_TrailSmoke_*` or other smoke helpers.
- Verify fireball renderer state:

```powershell
cd Server
python -m cli.main vfx particle info MCP_MageFireball_Test
```

Expected highlights:

- `renderer.renderMode: Stretch`
- `renderer.material: SmokeMat`

### Duplicate fireball objects by name

If `gameobject find` returns multiple IDs for the same name, name-based commands can hit the wrong object.

```powershell
cd Server
python -m cli.main gameobject find MCP_MageFireball_Test
```

Delete unwanted duplicates by ID:

```powershell
python -m cli.main gameobject delete --search-method by_id --force -- -12345
```

Note: negative IDs must use `--` before the ID so CLI parsing treats it as a target.
