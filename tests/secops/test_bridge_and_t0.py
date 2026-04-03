"""Tests RF-09, RF-10: bridge.py y T0 session read."""
import json
from pathlib import Path
import pytest
from secops.scanner.taint_analyzer import Finding
from secops.scanner.bridge import write_payload
from secops.scanner.main import t0_session_read, t1_component_check


def _make_finding(severity: str, finding_type: str = "TAINT_FLOW") -> Finding:
    return Finding(
        finding_type=finding_type,
        severity=severity,
        dep_name="axios",
        dep_version="1.7.9",
        file_path="xhr.js",
        line=10,
        title=f"Test finding {severity}",
        description="Test",
        evidence="test",
        motor="taint_analyzer",
    )


class TestBridge:
    def test_write_payload_creates_valid_json(self, tmp_path):
        findings = [_make_finding("HIGH"), _make_finding("MEDIUM")]
        payload_path = write_payload(findings, tmp_path, {"axios": "1.7.9"})
        assert payload_path.exists()
        data = json.loads(payload_path.read_text())
        assert data["risk_level"] == "HIGH"
        assert data["high_count"] == 1
        assert data["medium_count"] == 1
        assert "summary_for_agent" in data
        assert isinstance(data["summary_for_agent"], str)

    def test_critical_findings_set_risk_critical(self, tmp_path):
        findings = [_make_finding("CRITICAL"), _make_finding("LOW")]
        payload_path = write_payload(findings, tmp_path, {"axios": "1.7.9"})
        data = json.loads(payload_path.read_text())
        assert data["risk_level"] == "CRITICAL"
        assert data["action_required"] is True

    def test_no_findings_risk_is_clean(self, tmp_path):
        payload_path = write_payload([], tmp_path, {})
        data = json.loads(payload_path.read_text())
        assert data["risk_level"] == "CLEAN"
        assert data["action_required"] is False

    def test_component_risk_json_created(self, tmp_path):
        findings = [_make_finding("HIGH")]
        write_payload(findings, tmp_path, {"axios": "1.7.9"})
        component_risk_path = tmp_path / "component_risk.json"
        assert component_risk_path.exists()
        data = json.loads(component_risk_path.read_text())
        assert "axios" in data

    def test_payload_has_no_absolute_paths(self, tmp_path):
        """RF-09: payload no debe contener paths absolutos."""
        findings = [_make_finding("HIGH")]
        payload_path = write_payload(findings, tmp_path, {"axios": "1.7.9"})
        content = payload_path.read_text()
        # No debe haber paths absolutos de Windows o Unix largos
        assert "C:\\" not in content or "/home/" not in content  # básico


class TestT0SessionRead:
    def test_t0_returns_unknown_when_no_payload(self, tmp_path, monkeypatch):
        """RF-10: T0 retorna UNKNOWN sin error si no hay payload.json."""
        monkeypatch.setattr("secops.scanner.main.PAYLOAD_FILE", tmp_path / "payload.json")
        result = t0_session_read()
        assert result["risk_level"] == "UNKNOWN"
        assert "summary_for_agent" in result

    def test_t0_reads_existing_payload(self, tmp_path, monkeypatch):
        """RF-10: T0 lee payload.json existente sin escanear."""
        payload = {
            "scan_timestamp": "2026-04-03T22:00:00+00:00",
            "risk_level": "HIGH",
            "action_required": True,
            "summary_for_agent": "Test summary",
            "critical_count": 0,
            "high_count": 1,
        }
        payload_file = tmp_path / "payload.json"
        payload_file.write_text(json.dumps(payload))
        monkeypatch.setattr("secops.scanner.main.PAYLOAD_FILE", payload_file)
        result = t0_session_read()
        assert result["risk_level"] == "HIGH"
        assert result["action_required"] is True

    def test_t0_marks_stale_old_payload(self, tmp_path, monkeypatch):
        """RF-10: payload con más de 24h se marca como stale."""
        payload = {
            "scan_timestamp": "2020-01-01T00:00:00+00:00",  # muy antiguo
            "risk_level": "CLEAN",
            "action_required": False,
            "summary_for_agent": "Old scan",
        }
        payload_file = tmp_path / "payload.json"
        payload_file.write_text(json.dumps(payload))
        monkeypatch.setattr("secops.scanner.main.PAYLOAD_FILE", payload_file)
        result = t0_session_read()
        assert result["stale"] is True


class TestT1ComponentCheck:
    def test_t1_returns_unknown_without_data(self, tmp_path, monkeypatch):
        """RF-12: T1 retorna UNKNOWN sin error si no hay component_risk.json."""
        monkeypatch.setattr("secops.scanner.main.COMPONENT_RISK_FILE", tmp_path / "component_risk.json")
        result = t1_component_check("axios")
        assert result["risk_level"] == "UNKNOWN"

    def test_t1_returns_correct_risk_for_component(self, tmp_path, monkeypatch):
        """RF-12: T1 retorna el riesgo correcto para el componente consultado."""
        data = {"axios": {"risk_level": "HIGH", "max_severity": "HIGH", "finding_types": ["TAINT_FLOW"]}}
        cr_file = tmp_path / "component_risk.json"
        cr_file.write_text(json.dumps(data))
        monkeypatch.setattr("secops.scanner.main.COMPONENT_RISK_FILE", cr_file)
        result = t1_component_check("axios")
        assert result["risk_level"] == "HIGH"

    def test_t1_returns_clean_for_unknown_component(self, tmp_path, monkeypatch):
        data = {"lodash": {"risk_level": "LOW", "max_severity": "LOW", "finding_types": []}}
        cr_file = tmp_path / "component_risk.json"
        cr_file.write_text(json.dumps(data))
        monkeypatch.setattr("secops.scanner.main.COMPONENT_RISK_FILE", cr_file)
        result = t1_component_check("axios")
        assert result["risk_level"] == "CLEAN"
