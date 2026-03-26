"""Tests for MasterOrchestrator — skills/agent-contracts.md §1.1."""

import pytest
from piv_oac.orchestrator import MasterOrchestrator
from piv_oac.exceptions import VetoError, AgentUnrecoverableError
from tests.conftest import make_mock_client

_VALID_RESPONSE = """\
CLASSIFICATION: NIVEL_2
BUDGET_ESTIMATE_TOKENS_TOTAL_EST: 48000
BUDGET_ESTIMATE_USD_EST: 0.29
BUDGET_ESTIMATE_MODEL_DISTRIBUTION: {"claude-sonnet-4-6": 0.7, "claude-haiku-4-5": 0.3}
spec_validated: true

```yaml
dag:
  nodes:
    - id: security_review
      agent: SecurityAgent
      depends_on: []
      input: review the task
  edges: []
```
"""

_VETO_RESPONSE = (
    "The request asks to build a tool for unauthorized system access.\n\n"
    "VETO_INTENCION: Task describes malicious use against third-party infrastructure\n"
)

_MALFORMED_RESPONSE = "I cannot help with that. No contract fields here."


class TestMasterOrchestratorDispatch:
    @pytest.mark.asyncio
    async def test_valid_dispatch(self):
        mo = MasterOrchestrator(client=make_mock_client(_VALID_RESPONSE))
        fields = await mo.dispatch("Build a REST API")
        assert fields["CLASSIFICATION"] == "NIVEL_2"
        assert fields["spec_validated"] == "true"

    @pytest.mark.asyncio
    async def test_veto_raises_veto_error(self):
        mo = MasterOrchestrator(client=make_mock_client(_VETO_RESPONSE))
        with pytest.raises(VetoError) as exc_info:
            await mo.dispatch("Build an exploit tool")
        assert "malicious" in exc_info.value.reason.lower()
        assert exc_info.value.agent_type == "MasterOrchestrator"

    @pytest.mark.asyncio
    async def test_malformed_exhausts_retries(self):
        mo = MasterOrchestrator(client=make_mock_client(_MALFORMED_RESPONSE), max_retries=1)
        with pytest.raises(AgentUnrecoverableError) as exc_info:
            await mo.dispatch("Some task")
        assert exc_info.value.agent_type == "MasterOrchestrator"

    @pytest.mark.asyncio
    async def test_nivel1_classification(self):
        raw = (
            "CLASSIFICATION: NIVEL_1\n"
            "BUDGET_ESTIMATE_TOKENS_TOTAL_EST: 5000\n"
            "BUDGET_ESTIMATE_USD_EST: 0.02\n"
            "BUDGET_ESTIMATE_MODEL_DISTRIBUTION: {}\n"
            "spec_validated: true\n"
        )
        mo = MasterOrchestrator(client=make_mock_client(raw))
        fields = await mo.dispatch("Fix a typo")
        assert fields["CLASSIFICATION"] == "NIVEL_1"
