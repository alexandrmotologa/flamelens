"""Integration tests for CI quality gates, advisor, and spikes CLI commands."""

from pathlib import Path

from typer.testing import CliRunner

from flamelens.cli import app

runner = CliRunner()


def test_quality_gate_fails_when_memory_budget_exceeded(tmp_path):
    fixture_script = Path("tests/fixtures/sample_leak_app.py")
    profile_out = tmp_path / "budget_profile.json"

    # Set unrealistically low memory budget (0.01 MB = ~10 KB) to trigger quality gate failure
    result = runner.invoke(
        app,
        [
            "profile",
            str(fixture_script),
            "-o",
            str(profile_out),
            "--max-mem",
            "0.01",
            "-f",
            "none",
        ],
    )
    # Must fail with exit code 2
    assert result.exit_code == 2
    assert "CI QUALITY GATE FAILED" in result.stdout
    assert "Memory budget exceeded" in result.stdout


def test_cli_analyze_command(tmp_path):
    sample_folded = Path("tests/fixtures/sample.folded")
    assert sample_folded.exists()

    result = runner.invoke(app, ["analyze", str(sample_folded), "--min-impact-pct", "10.0"])
    assert result.exit_code == 0
    assert "FlameLens Optimization Advisory" in result.stdout
    assert "Hibernate.loadLazyList" in result.stdout


def test_cli_spikes_command(tmp_path):
    fixture_script = Path("tests/fixtures/sample_leak_app.py")
    profile_out = tmp_path / "spike_profile.json"

    # Run profile
    runner.invoke(
        app,
        ["profile", str(fixture_script), "-o", str(profile_out), "-f", "none"],
    )
    assert profile_out.exists()

    result = runner.invoke(app, ["spikes", str(profile_out)])
    assert result.exit_code == 0
