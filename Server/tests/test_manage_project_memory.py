"""Tests for manage_project_memory tool."""
import json
import tempfile
from pathlib import Path

import pytest

from services.tools.manage_project_memory import (
    ProjectRules,
    _parse_rules_file,
    _get_default_rules_content,
    _rules_to_markdown,
    _find_rules_file,
    _get_rules_path,
)


class TestProjectRules:
    """Tests for ProjectRules model."""

    def test_default_rules(self):
        rules = ProjectRules()
        assert rules.version == "1.0"
        assert rules.naming_conventions == {}
        assert rules.scene_organization == []
        assert rules.code_style == []
        assert rules.validation_rules == []
        assert rules.custom_rules == {}

    def test_rules_with_data(self):
        rules = ProjectRules(
            version="2.0",
            naming_conventions={"Prefabs": "PascalCase"},
            scene_organization=["Use folders"],
            code_style=["Cache components"],
            validation_rules=["No missing scripts"],
            custom_rules={"team": "MyTeam"}
        )
        assert rules.version == "2.0"
        assert rules.naming_conventions["Prefabs"] == "PascalCase"


class TestRulesParsing:
    """Tests for rules file parsing."""

    def test_parse_default_rules(self):
        content = _get_default_rules_content()
        rules = _parse_rules_file(content)
        
        # Should extract naming conventions
        assert len(rules.naming_conventions) > 0
        assert "Prefabs" in rules.naming_conventions
        
        # Should extract scene organization rules
        assert len(rules.scene_organization) > 0
        
        # Should extract code style rules
        assert len(rules.code_style) > 0
        
        # Should extract validation rules
        assert len(rules.validation_rules) > 0

    def test_parse_custom_rules(self):
        content = """# Unity MCP Project Rules

## Naming Conventions
- Scripts: PascalCase
- Materials: Snake_Case

## Scene Organization
- Group objects in folders

## Code Style
- Use explicit types

## Validation Rules
- Check null references

## Custom Rules
- MyRule: Value
"""
        rules = _parse_rules_file(content)
        
        assert rules.naming_conventions["Scripts"] == "PascalCase"
        assert rules.naming_conventions["Materials"] == "Snake_Case"
        assert "Group objects in folders" in rules.scene_organization
        assert "Use explicit types" in rules.code_style
        assert "Check null references" in rules.validation_rules

    def test_rules_round_trip(self):
        """Test that parsing and generating results in consistent data."""
        original_content = _get_default_rules_content()
        rules = _parse_rules_file(original_content)
        
        # Convert to markdown and back
        markdown = _rules_to_markdown(rules)
        reparsed_rules = _parse_rules_file(markdown)
        
        # Key counts should match
        assert len(reparsed_rules.naming_conventions) == len(rules.naming_conventions)
        assert len(reparsed_rules.scene_organization) == len(rules.scene_organization)


class TestFileOperations:
    """Tests for file operations."""

    def test_find_rules_file_default(self, tmp_path):
        """Test finding default rules file."""
        # Create .unity-mcp-rules file
        rules_file = tmp_path / ".unity-mcp-rules"
        rules_file.write_text("test content")
        
        found = _find_rules_file(str(tmp_path))
        assert found == rules_file

    def test_find_rules_file_alt(self, tmp_path):
        """Test finding alternative rules file."""
        # Create UnityMCPRules.md file
        rules_file = tmp_path / "UnityMCPRules.md"
        rules_file.write_text("test content")
        
        found = _find_rules_file(str(tmp_path))
        assert found == rules_file

    def test_find_rules_file_not_found(self, tmp_path):
        """Test when no rules file exists."""
        found = _find_rules_file(str(tmp_path))
        assert found is None

    def test_get_rules_path_default(self, tmp_path):
        """Test getting default rules path."""
        path = _get_rules_path(str(tmp_path))
        assert path.name == ".unity-mcp-rules"
        assert path.parent == tmp_path

    def test_get_rules_path_custom(self, tmp_path):
        """Test getting custom rules path."""
        path = _get_rules_path(str(tmp_path), "custom-rules.md")
        assert path.name == "custom-rules.md"

    def test_get_rules_path_relative(self, tmp_path):
        """Test getting relative rules path."""
        path = _get_rules_path(str(tmp_path), "docs/rules.md")
        assert path.name == "rules.md"
        assert "docs" in str(path)


class TestMarkdownGeneration:
    """Tests for markdown generation."""

    def test_rules_to_markdown_structure(self):
        rules = ProjectRules(
            naming_conventions={"Prefabs": "PascalCase"},
            scene_organization=["Use folders"],
            code_style=["Cache components"],
            validation_rules=["Check nulls"],
        )
        
        markdown = _rules_to_markdown(rules)
        
        # Should contain all sections
        assert "## Naming Conventions" in markdown
        assert "## Scene Organization" in markdown
        assert "## Code Style" in markdown
        assert "## Validation Rules" in markdown
        
        # Should contain the data
        assert "PascalCase" in markdown
        assert "Use folders" in markdown


class TestIntegration:
    """Integration-style tests that require mocking Unity connection."""
    
    @pytest.mark.asyncio
    async def test_load_rules_returns_defaults_when_no_file(self, tmp_path, monkeypatch):
        """Test that load_rules returns default rules when no file exists."""
        from services.tools.manage_project_memory import _load_rules
        
        result = await _load_rules(str(tmp_path))
        
        assert result["success"] is True
        assert result["data"]["source"] == "default"
        assert "rules" in result["data"]

    @pytest.mark.asyncio
    async def test_load_rules_reads_existing_file(self, tmp_path, monkeypatch):
        """Test that load_rules reads existing rules file."""
        from services.tools.manage_project_memory import _load_rules
        
        # Create a rules file
        rules_file = tmp_path / ".unity-mcp-rules"
        rules_file.write_text(_get_default_rules_content())
        
        result = await _load_rules(str(tmp_path))
        
        assert result["success"] is True
        assert "default" not in result["data"]["source"]
        assert result["data"]["path"] == str(rules_file)

    @pytest.mark.asyncio
    async def test_save_rules_creates_file(self, tmp_path, monkeypatch):
        """Test that save_rules creates a rules file."""
        from services.tools.manage_project_memory import _save_rules
        
        rules_data = {
            "version": "1.0",
            "naming_conventions": {"Scripts": "PascalCase"},
            "scene_organization": ["Use folders"],
            "code_style": ["Cache components"],
            "validation_rules": ["Check nulls"],
            "custom_rules": {}
        }
        
        result = await _save_rules(str(tmp_path), rules_data=rules_data)
        
        assert result["success"] is True
        assert Path(result["data"]["path"]).exists()

    @pytest.mark.asyncio
    async def test_summarize_conventions_markdown(self, tmp_path, monkeypatch):
        """Test summarize_conventions with markdown format."""
        from services.tools.manage_project_memory import _summarize_conventions
        
        result = await _summarize_conventions(str(tmp_path), fmt="markdown")
        
        assert result["success"] is True
        assert "markdown" in result["data"]

    @pytest.mark.asyncio
    async def test_summarize_conventions_json(self, tmp_path, monkeypatch):
        """Test summarize_conventions with json format."""
        from services.tools.manage_project_memory import _summarize_conventions
        
        result = await _summarize_conventions(str(tmp_path), fmt="json")
        
        assert result["success"] is True
        assert "naming_conventions" in result["data"]

    @pytest.mark.asyncio
    async def test_get_active_rules_all(self, tmp_path, monkeypatch):
        """Test get_active_rules with all categories."""
        from services.tools.manage_project_memory import _get_active_rules
        
        result = await _get_active_rules(str(tmp_path), category="all")
        
        assert result["success"] is True
        assert result["data"]["category"] == "all"

    @pytest.mark.asyncio
    async def test_get_active_rules_naming(self, tmp_path, monkeypatch):
        """Test get_active_rules with naming category."""
        from services.tools.manage_project_memory import _get_active_rules
        
        result = await _get_active_rules(str(tmp_path), category="naming")
        
        assert result["success"] is True
        assert "naming" in result["data"]["rules"]
        assert "organization" not in result["data"]["rules"]
