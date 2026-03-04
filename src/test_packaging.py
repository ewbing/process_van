from pathlib import Path
import tomllib


def test_console_script_entrypoint_configured():
    project_root = Path(__file__).resolve().parent.parent
    pyproject_path = project_root / "pyproject.toml"

    config = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    scripts = config["project"]["scripts"]

    assert scripts["process_van"] == "process_van:cli_entrypoint"
