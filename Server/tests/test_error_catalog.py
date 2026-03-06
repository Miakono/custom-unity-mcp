import json

from services.error_catalog import build_error_catalog, export_error_catalog_artifacts


def test_build_error_catalog_includes_stable_domains_and_codes():
    catalog = build_error_catalog()

    assert catalog["generated_from"] == "fork_error_contract_registry"
    assert catalog["domain_count"] >= 2
    assert catalog["stable_code_count"] >= 18
    assert any(domain["id"] == "script_editing" for domain in catalog["domains"])
    assert any(domain["id"] == "scriptable_objects" for domain in catalog["domains"])

    codes = {
        entry["code"]
        for domain in catalog["domains"]
        for entry in domain["entries"]
    }
    assert "missing_field" in codes
    assert "asset_create_failed" in codes


def test_export_error_catalog_artifacts_writes_expected_files(tmp_path):
    result = export_error_catalog_artifacts(tmp_path)

    assert result["stable_code_count"] >= 18
    assert result["domain_count"] >= 2
    assert len(result["written_files"]) == 2

    catalog_path = tmp_path / "error_catalog.json"
    readme_path = tmp_path / "README.md"
    assert catalog_path.exists()
    assert readme_path.exists()

    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    assert catalog["stable_code_count"] >= 18
    readme = readme_path.read_text(encoding="utf-8")
    assert "Unity MCP Error Catalog" in readme
    assert "`missing_field`" in readme
    assert "`asset_create_failed`" in readme
