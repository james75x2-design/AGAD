import os
import yaml


def test_mcp_yaml_is_valid():
    yaml_path = os.path.join(os.path.dirname(__file__), os.pardir, "mcp", "local-mcp.yaml")
    with open(yaml_path, "r", encoding="utf-8") as fh:
        loaded = yaml.safe_load(fh)

    assert isinstance(loaded, dict)
    assert loaded.get("mcp", {}).get("name") == "agad-local-mcp"
