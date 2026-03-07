# Unity MCP Project Rules

## Naming Conventions
- Prefabs: PascalCase with "Prefab" suffix (e.g., "PlayerPrefab")
- Scripts: PascalCase, noun-first (e.g., "PlayerController")
- Materials: Category_Purpose (e.g., "Env_Grass", "Char_Skin")
- Textures: Type_Description_Size (e.g., "Tex_Grass_512")
- Animations: Action_Layer (e.g., "Run_Layer1", "Attack_Base")

## Scene Organization
- Use empty GameObjects as folders (e.g., "Environment", "Lighting", "UI")
- Main camera at origin or designated position
- Lights in "Lighting" folder
- UI elements in "UI" folder with Canvas as parent
- Keep hierarchy depth reasonable (max 5-6 levels)

## Code Style
- Use [SerializeField] for inspector fields instead of public
- Avoid FindObjectOfType in Update - cache in Awake/Start
- Cache component references in private fields
- Use PascalCase for public methods, camelCase for private
- Add XML documentation for public APIs

## Validation Rules
- No missing script references on GameObjects
- All materials should be assigned
- No unnamed GameObjects (should have descriptive names)
- No duplicate GameObject names at same hierarchy level
- Check for unused using statements
- Ensure all scenes in build settings exist

## Custom Rules
Add your project-specific rules here.
