"""End-to-end integration tests for FlameLens CLI."""

from pathlib import Path

from typer.testing import CliRunner

from flamelens.cli import app

runner = CliRunner()


def test_cli_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "FlameLens version" in result.stdout


def test_cli_profile_and_view(tmp_path):
    fixture_script = Path("tests/fixtures/sample_leak_app.py")
    assert fixture_script.exists()

    profile_json = tmp_path / "test_profile.json"

    # Profile target script
    result = runner.invoke(
        app,
        ["profile", str(fixture_script), "-o", str(profile_json), "-f", "ascii"],
    )
    assert result.exit_code == 0
    assert profile_json.exists()
    assert "Profile saved to:" in result.stdout

    # View saved profile in ASCII mode
    view_result = runner.invoke(
        app,
        ["view", str(profile_json), "-f", "ascii"],
    )
    assert view_result.exit_code == 0
    assert "FlameLens Profile" in view_result.stdout


def test_cli_export_html_and_folded(tmp_path):
    sample_folded = Path("tests/fixtures/sample.folded")
    assert sample_folded.exists()

    out_html = tmp_path / "flame.html"
    out_folded = tmp_path / "exported.folded"
    out_json = tmp_path / "exported.json"

    # Export to HTML
    res_html = runner.invoke(
        app,
        ["export", str(sample_folded), "-f", "html", "-o", str(out_html)],
    )
    assert res_html.exit_code == 0
    assert out_html.exists()
    assert "<!DOCTYPE html>" in out_html.read_text(encoding="utf-8")

    # Export to folded
    res_folded = runner.invoke(
        app,
        ["export", str(sample_folded), "-f", "folded", "-o", str(out_folded)],
    )
    assert res_folded.exit_code == 0
    assert out_folded.exists()

    # Export to json
    res_json = runner.invoke(
        app,
        ["export", str(sample_folded), "-f", "json", "-o", str(out_json)],
    )
    assert res_json.exit_code == 0
    assert out_json.exists()


def test_cli_diff_workflow(tmp_path):
    base_file = Path("tests/fixtures/sample.folded")
    diff_json = tmp_path / "diff.json"

    result = runner.invoke(
        app,
        ["diff", str(base_file), str(base_file), "-f", "ascii", "-o", str(diff_json)],
    )
    assert result.exit_code == 0
    assert diff_json.exists()
    assert "FlameLens Diff:" in result.stdout
