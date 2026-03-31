"""
piv-oac — Python SDK for the PIV/OAC framework.

Public exports:
    MasterOrchestrator   — top-level pipeline client
    AgentBase            — abstract base for all agents
    SecurityAgent        — security review agent
    AuditAgent           — RF coverage and scope audit agent
    CoherenceAgent       — Gate-1 coherence check agent
    StandardsAgent       — Gate-2 code quality and coverage agent
    ComplianceAgent      — Gate-3 legal/regulatory evaluation agent
    DomainOrchestrator   — domain-level task coordinator
    SpecialistAgent      — atomic task implementor
    DAGNode              — single task node in the orchestration DAG
    DAGValidator         — validates DAGs before agent launch
    CyclicDependencyError — raised when the DAG contains a cycle
    PIVOACError          — base exception class

Version: 0.1.0
"""

from piv_oac.agents.audit import AuditAgent
from piv_oac.agents.base import AgentBase
from piv_oac.agents.evaluation_agent import EvaluationAgent, FuncInput, SecInput, QualInput, CohInput, FootInput, ScoringResult
from piv_oac.agents.research_orchestrator import ResearchOrchestrator
from piv_oac.checkpoint.validator import CheckpointValidator, ValidationReport
from piv_oac.agents.coherence import CoherenceAgent
from piv_oac.agents.compliance import ComplianceAgent, COMPLIANCE_DISCLAIMER
from piv_oac.agents.domain_orchestrator import DomainOrchestrator, WorktreeSpec
from piv_oac.agents.security import SecurityAgent
from piv_oac.agents.specialist import SpecialistAgent
from piv_oac.agents.standards import StandardsAgent
from piv_oac.exceptions import (
    AgentUnrecoverableError,
    GateRejectedError,
    MalformedOutputError,
    PIVOACError,
    VetoError,
)
from piv_oac.dag import CyclicDependencyError, DAGNode, DAGValidator
from piv_oac.orchestrator import MasterOrchestrator

__version__ = "0.1.0"

__all__ = [
    "__version__",
    # Orchestrators
    "MasterOrchestrator",
    "DomainOrchestrator",
    "WorktreeSpec",
    # Control environment agents
    "SecurityAgent",
    "AuditAgent",
    "CoherenceAgent",
    "StandardsAgent",
    "ComplianceAgent",
    "COMPLIANCE_DISCLAIMER",
    # Execution agents
    "SpecialistAgent",
    # Base
    "AgentBase",
    # Research
    "ResearchOrchestrator",
    # Checkpoint
    "CheckpointValidator",
    "ValidationReport",
    # Evaluation
    "EvaluationAgent",
    "FuncInput",
    "SecInput",
    "QualInput",
    "CohInput",
    "FootInput",
    "ScoringResult",
    # DAG utilities
    "DAGNode",
    "DAGValidator",
    "CyclicDependencyError",
    # Exceptions
    "PIVOACError",
    "AgentUnrecoverableError",
    "GateRejectedError",
    "MalformedOutputError",
    "VetoError",
]
