# GitHub Package Install

This fork can be installed into a Unity project directly from a Git repository because the Unity package lives in `MCPForUnity/`.

## Unity Package Manager format

Use a dependency entry shaped like this:

```json
{
  "dependencies": {
    "com.customgamedev.unity-mcp": "https://github.com/Miakono/custom-unity-mcp.git?path=/MCPForUnity#main"
  }
}
```

Notes:
- `?path=/MCPForUnity` is required because the Unity package is not at repo root.
- Replace `#main` with a tag, branch, or commit SHA when you want a pinned install.
- Git installs now derive the Python server source from the same repository automatically.
- If you are developing the fork locally as a Package Manager local package, the plugin will resolve the sibling `Server` directory automatically.

## Installer script

This repo now includes:

`Scripts/Install-MCPForUnityGitPackage.ps1`

Example:

```powershell
.\Scripts\Install-MCPForUnityGitPackage.ps1 `
  -UnityProjectPath "C:\Projects\MyGame" `
  -GitUrl "https://github.com/Miakono/custom-unity-mcp" `
  -GitRef "main"
```

That updates:

`<UnityProject>\Packages\manifest.json`

with:

`com.customgamedev.unity-mcp = https://github.com/Miakono/custom-unity-mcp.git?path=/MCPForUnity#main`

## Manual install

1. Open the Unity project.
2. Open `Packages/manifest.json`.
3. Add or update the dependency entry above.
4. Save the file.
5. Let Unity resolve and import the package.
6. If you want to override the inferred server source, open `Window > MCP for Unity > Advanced` and choose `Select server folder...`.

## Verification

After Unity imports the package:

1. Open `Window > MCP for Unity`.
2. Wait for compilation to finish.
3. Check the Console for package compile errors.
4. Verify these surfaces resolve:
   - `get_subagent_profiles`
   - `get_validation_profiles`
   - `validate_project_state`
