# Custom Unity MCP

This project is derived from CoplayDev/unity-mcp (MIT License).

Upstream source:
- https://github.com/Miakono/custom-unity-mcp (forked from https://github.com/CoplayDev/unity-mcp)

Included upstream files:
- MCPForUnity/
- Server/
- LICENSE
- UPSTREAM_README.md

Initial customization targets:
1. Add project-specific workflow tools for your game.
2. Add stronger validation/reporting tools (compile, scene checks, prefab integrity).
3. Add progress/log notifications for long-running tasks.
4. Add registry-backed subagent artifacts so MCP clients can route work through Unity specialists.

Recent fork additions:
- Server-generated subagent catalog and export tool.
- Server-generated live tool catalog with action-level capability contracts and parameter metadata.
- Server-generated error catalog with stable codes and operational response patterns.
- Git-based Unity package installer script for `?path=/MCPForUnity` installs.
- Unity plugin workflow catalog with a dedicated `Workflows` tab.
- Unity plugin validation profile catalog exposed as a resource for audit/readiness discovery.
- Read-only Unity audits for scene integrity and prefab integrity.
- Initial `Docs/ERROR_CODES.md` for current machine-readable server edit errors.
- Cold-start-safe artifact export for tool catalogs and subagent bundles outside normal server startup.
