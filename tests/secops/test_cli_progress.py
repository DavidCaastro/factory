import json


def test_scan_progress_overwrites_lines(capsys, monkeypatch, tmp_path):
    import secops.scanner.main as main
    from secops.scanner.cli import run
    from secops.scanner.progress import ProgressEvent

    def fake_run_full_scan(_root, dep_filter=None, method_filter=None, on_progress=None, reports_dir=None):
        assert dep_filter is None
        assert method_filter is None
        if on_progress is not None:
            on_progress(ProgressEvent(1, 2, "fetch", "Descargando demo@1.0.0"))
            on_progress(ProgressEvent(2, 2, "output", "Generando reporte"))
        return {
            "findings_count": 0,
            "risk_level": "CLEAN",
            "report_path": str(tmp_path / "report.md"),
            "deps_analyzed": 1,
        }

    monkeypatch.setattr(main, "run_full_scan", fake_run_full_scan)

    exit_code = run(["scan", "--root", str(tmp_path), "--progress"])
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "\x1b[2K" in out
    assert "Generando reporte" in out


def test_scan_json_disables_progress_output(capsys, monkeypatch, tmp_path):
    import secops.scanner.main as main
    from secops.scanner.cli import run

    def fake_run_full_scan(_root, dep_filter=None, method_filter=None, on_progress=None, reports_dir=None):
        assert dep_filter is None
        assert method_filter is None
        assert on_progress is not None
        return {
            "findings_count": 0,
            "risk_level": "CLEAN",
            "report_path": str(tmp_path / "report.md"),
            "deps_analyzed": 0,
        }

    monkeypatch.setattr(main, "run_full_scan", fake_run_full_scan)

    exit_code = run(["scan", "--root", str(tmp_path), "--json", "--progress"])
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "\x1b[2K" not in out
    json_start = out.find("{")
    data = json.loads(out[json_start:])
    assert data["risk_level"] == "CLEAN"
