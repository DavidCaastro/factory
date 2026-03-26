"""Tests for DAG validator — cycle detection, topological order, parallel groups."""

import pytest
from piv_oac.dag import DAGNode, DAGValidator, CyclicDependencyError


class TestDAGNode:
    def test_node_empty_task_id_raises(self):
        with pytest.raises(ValueError):
            DAGNode("")

    def test_node_whitespace_task_id_raises(self):
        with pytest.raises(ValueError):
            DAGNode("   ")

    def test_node_defaults_no_deps(self):
        node = DAGNode("A")
        assert node.dependencies == []

    def test_node_with_deps(self):
        node = DAGNode("B", dependencies=["A"])
        assert node.dependencies == ["A"]


class TestDAGValidatorValid:
    def test_single_node_is_valid(self):
        validator = DAGValidator([DAGNode("A")])
        validator.validate()  # no raise

    def test_linear_chain_is_valid(self):
        nodes = [DAGNode("A"), DAGNode("B", ["A"]), DAGNode("C", ["B"])]
        DAGValidator(nodes).validate()

    def test_diamond_graph_is_valid(self):
        nodes = [
            DAGNode("A"),
            DAGNode("B", ["A"]),
            DAGNode("C", ["A"]),
            DAGNode("D", ["B", "C"]),
        ]
        DAGValidator(nodes).validate()

    def test_multiple_roots_is_valid(self):
        nodes = [DAGNode("A"), DAGNode("B"), DAGNode("C", ["A", "B"])]
        DAGValidator(nodes).validate()

    def test_empty_graph_is_valid(self):
        DAGValidator([]).validate()


class TestCycleDetection:
    def test_self_loop_raises(self):
        nodes = [DAGNode("A", ["A"])]
        with pytest.raises(CyclicDependencyError) as exc_info:
            DAGValidator(nodes).validate()
        assert "A" in exc_info.value.cycle

    def test_two_node_cycle_raises(self):
        nodes = [DAGNode("A", ["B"]), DAGNode("B", ["A"])]
        with pytest.raises(CyclicDependencyError):
            DAGValidator(nodes).validate()

    def test_three_node_cycle_raises(self):
        nodes = [
            DAGNode("A", ["C"]),
            DAGNode("B", ["A"]),
            DAGNode("C", ["B"]),
        ]
        with pytest.raises(CyclicDependencyError) as exc_info:
            DAGValidator(nodes).validate()
        assert len(exc_info.value.cycle) >= 2

    def test_cycle_error_message_contains_arrow(self):
        nodes = [DAGNode("X", ["X"])]
        with pytest.raises(CyclicDependencyError) as exc_info:
            DAGValidator(nodes).validate()
        assert "→" in str(exc_info.value)

    def test_partial_graph_with_cycle_raises(self):
        # A→B→C→B (cycle in the middle)
        nodes = [
            DAGNode("A"),
            DAGNode("B", ["A", "C"]),
            DAGNode("C", ["B"]),
        ]
        with pytest.raises(CyclicDependencyError):
            DAGValidator(nodes).validate()


class TestUnknownDependency:
    def test_unknown_dep_raises_value_error(self):
        nodes = [DAGNode("A", ["NONEXISTENT"])]
        with pytest.raises(ValueError, match="unknown task"):
            DAGValidator(nodes).validate()


class TestTopologicalOrder:
    def test_single_node_order(self):
        order = DAGValidator([DAGNode("A")]).topological_order()
        assert order == ["A"]

    def test_linear_chain_order(self):
        nodes = [DAGNode("C", ["B"]), DAGNode("B", ["A"]), DAGNode("A")]
        order = DAGValidator(nodes).topological_order()
        assert order.index("A") < order.index("B") < order.index("C")

    def test_diamond_order_respects_deps(self):
        nodes = [
            DAGNode("A"),
            DAGNode("B", ["A"]),
            DAGNode("C", ["A"]),
            DAGNode("D", ["B", "C"]),
        ]
        order = DAGValidator(nodes).topological_order()
        assert order.index("A") < order.index("B")
        assert order.index("A") < order.index("C")
        assert order.index("B") < order.index("D")
        assert order.index("C") < order.index("D")

    def test_cycle_prevents_topological_order(self):
        nodes = [DAGNode("A", ["B"]), DAGNode("B", ["A"])]
        with pytest.raises(CyclicDependencyError):
            DAGValidator(nodes).topological_order()

    def test_all_nodes_present_in_order(self):
        nodes = [DAGNode("A"), DAGNode("B", ["A"]), DAGNode("C", ["A"])]
        order = DAGValidator(nodes).topological_order()
        assert set(order) == {"A", "B", "C"}


class TestParallelGroups:
    def test_independent_nodes_in_one_group(self):
        nodes = [DAGNode("A"), DAGNode("B"), DAGNode("C")]
        groups = DAGValidator(nodes).parallel_groups()
        assert len(groups) == 1
        assert set(groups[0]) == {"A", "B", "C"}

    def test_linear_chain_one_per_group(self):
        nodes = [DAGNode("A"), DAGNode("B", ["A"]), DAGNode("C", ["B"])]
        groups = DAGValidator(nodes).parallel_groups()
        assert len(groups) == 3
        assert groups[0] == ["A"]
        assert groups[1] == ["B"]
        assert groups[2] == ["C"]

    def test_diamond_produces_three_levels(self):
        nodes = [
            DAGNode("A"),
            DAGNode("B", ["A"]),
            DAGNode("C", ["A"]),
            DAGNode("D", ["B", "C"]),
        ]
        groups = DAGValidator(nodes).parallel_groups()
        assert groups[0] == ["A"]
        assert set(groups[1]) == {"B", "C"}
        assert groups[2] == ["D"]

    def test_empty_graph_returns_empty_groups(self):
        groups = DAGValidator([]).parallel_groups()
        assert groups == []

    def test_cycle_prevents_parallel_groups(self):
        nodes = [DAGNode("A", ["B"]), DAGNode("B", ["A"])]
        with pytest.raises(CyclicDependencyError):
            DAGValidator(nodes).parallel_groups()
