from pathlib import Path


def test_run_full_scan_emits_progress_events(tmp_path, monkeypatch):
    import secops.scanner.ast_engine as ast_engine
    import secops.scanner.behavioral_delta as behavioral_delta
    import secops.scanner.bridge as bridge
    import secops.scanner.contract_verifier as contract_verifier
    import secops.scanner.detect as detect
    import secops.scanner.fetcher as fetcher
    import secops.scanner.impact as impact
    import secops.scanner.main as main
    import secops.scanner.report as report
    import secops.scanner.taint_analyzer as taint_analyzer

    manifest = tmp_path / "requirements.txt"
    manifest.write_text("demo==1.0.0\n", encoding="utf-8")

    def fake_detect_languages(_root):
        return {"python": [manifest]}

    def fake_extract_dependencies(_manifest_path: Path):
        return [{"name": "demo", "version_spec": "==1.0.0", "language": "python"}]

    def fake_fetch_dependency(_name, _version, _language, _cache_dir):
        source_dir = tmp_path / "source"
        source_dir.mkdir(exist_ok=True)
        return source_dir

    monkeypatch.setattr(detect, "detect_languages", fake_detect_languages)
    monkeypatch.setattr(detect, "extract_dependencies", fake_extract_dependencies)
    monkeypatch.setattr(fetcher, "fetch_dependency", fake_fetch_dependency)
    monkeypatch.setattr(ast_engine, "parse_source_tree", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(taint_analyzer, "analyze", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(contract_verifier, "analyze", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(behavioral_delta, "analyze", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(report, "generate_report", lambda *_args, **_kwargs: tmp_path / "report.md")
    monkeypatch.setattr(impact, "write_impact", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(bridge, "write_payload", lambda *_args, **_kwargs: tmp_path / "payload.json")

    events = []
    main.run_full_scan(tmp_path, on_progress=events.append)

    assert events
    assert events[0].phase == "detect"
    assert any(evt.phase == "fetch" and "demo@1.0.0" in evt.message for evt in events)
    assert events[-1].phase == "output"
    assert events[-1].completed_steps == events[-1].total_steps
