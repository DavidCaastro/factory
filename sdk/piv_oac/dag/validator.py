"""
PIV/OAC DAG Validator — detects cycles and validates dependency graphs.

Used by the MasterOrchestrator to verify task graphs before launching
any agents (FASE 1 pre-condition).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence


class CyclicDependencyError(Exception):
    """Raised when a cycle is detected in the task DAG."""

    def __init__(self, cycle: list[str]) -> None:
        self.cycle = cycle
        cycle_str = " → ".join(cycle)
        super().__init__(f"Cycle detected in DAG: {cycle_str}")


@dataclass
class DAGNode:
    """Represents a single task node in the orchestration DAG."""

    task_id: str
    dependencies: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.task_id or not self.task_id.strip():
            raise ValueError("task_id must be a non-empty string")


class DAGValidator:
    """
    Validates a directed acyclic graph of task nodes.

    Usage::

        nodes = [
            DAGNode("A"),
            DAGNode("B", dependencies=["A"]),
            DAGNode("C", dependencies=["A", "B"]),
        ]
        validator = DAGValidator(nodes)
        validator.validate()  # raises CyclicDependencyError if cycle found
        order = validator.topological_order()
    """

    def __init__(self, nodes: Sequence[DAGNode]) -> None:
        self._nodes: dict[str, DAGNode] = {n.task_id: n for n in nodes}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate(self) -> None:
        """
        Check the graph for cycles and undefined dependency references.

        Raises:
            CyclicDependencyError: if a cycle is detected.
            ValueError: if a dependency references an unknown task_id.
        """
        self._check_unknown_deps()
        self._dfs_cycle_check()

    def topological_order(self) -> list[str]:
        """
        Return task IDs in a valid execution order (no task before its deps).

        Raises:
            CyclicDependencyError: if a cycle is present (calls validate first).
        """
        self.validate()
        return self._kahn_sort()

    def parallel_groups(self) -> list[list[str]]:
        """
        Partition tasks into sequential waves where all tasks in a wave
        can run in parallel (all their dependencies belong to earlier waves).

        Raises:
            CyclicDependencyError: if a cycle is present.
        """
        self.validate()
        return self._compute_levels()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _check_unknown_deps(self) -> None:
        known = set(self._nodes)
        for node in self._nodes.values():
            for dep in node.dependencies:
                if dep not in known:
                    raise ValueError(
                        f"Task '{node.task_id}' depends on unknown task '{dep}'"
                    )

    def _dfs_cycle_check(self) -> None:
        """Iterative DFS with three-color marking (WHITE/GRAY/BLACK)."""
        WHITE, GRAY, BLACK = 0, 1, 2
        color: dict[str, int] = {tid: WHITE for tid in self._nodes}
        parent: dict[str, str | None] = {tid: None for tid in self._nodes}

        for start in self._nodes:
            if color[start] != WHITE:
                continue
            stack = [(start, False)]
            while stack:
                tid, returning = stack.pop()
                if returning:
                    color[tid] = BLACK
                    continue
                if color[tid] == GRAY:
                    # reconstruct cycle path
                    cycle = self._reconstruct_cycle(tid, parent)
                    raise CyclicDependencyError(cycle)
                color[tid] = GRAY
                stack.append((tid, True))  # re-push to mark BLACK on return
                for dep in self._nodes[tid].dependencies:
                    if color[dep] == GRAY:
                        cycle = self._reconstruct_cycle(dep, parent)
                        raise CyclicDependencyError(cycle)
                    if color[dep] == WHITE:
                        parent[dep] = tid
                        stack.append((dep, False))

    def _reconstruct_cycle(
        self, cycle_node: str, parent: dict[str, str | None]
    ) -> list[str]:
        path = [cycle_node]
        cur: str | None = parent.get(cycle_node)
        visited_in_path: set[str] = {cycle_node}
        while cur is not None and cur not in visited_in_path:
            path.append(cur)
            visited_in_path.add(cur)
            cur = parent.get(cur)
        path.append(cycle_node)
        path.reverse()
        return path

    def _kahn_sort(self) -> list[str]:
        from collections import deque

        in_degree = {tid: 0 for tid in self._nodes}
        for node in self._nodes.values():
            for dep in node.dependencies:
                in_degree[node.task_id] += 1

        # Build adjacency: dep → list of tasks that depend on it
        adj: dict[str, list[str]] = {tid: [] for tid in self._nodes}
        for node in self._nodes.values():
            for dep in node.dependencies:
                adj[dep].append(node.task_id)

        queue: deque[str] = deque(
            tid for tid, deg in in_degree.items() if deg == 0
        )
        order: list[str] = []
        while queue:
            tid = queue.popleft()
            order.append(tid)
            for dependent in adj[tid]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
        return order

    def _compute_levels(self) -> list[list[str]]:
        """Assign each task to a wave (level) based on its longest dep chain."""
        level: dict[str, int] = {}

        def get_level(tid: str) -> int:
            if tid in level:
                return level[tid]
            node = self._nodes[tid]
            if not node.dependencies:
                level[tid] = 0
            else:
                level[tid] = 1 + max(get_level(dep) for dep in node.dependencies)
            return level[tid]

        for tid in self._nodes:
            get_level(tid)

        max_level = max(level.values(), default=-1)
        groups: list[list[str]] = [[] for _ in range(max_level + 1)]
        for tid, lv in level.items():
            groups[lv].append(tid)
        return [sorted(g) for g in groups]
