"""Tests for engine/decision_tree.py."""

import pytest

from hexmind.engine.decision_tree import DecisionTree
from hexmind.models.config import DiscussionConfig
from hexmind.models.tree import NodeStatus, TreeNode, Verdict


class TestCreateRoot:
    def test_creates_root(self):
        dt = DecisionTree(DiscussionConfig())
        root = dt.create_root("Should we use K8s?")
        assert root.question == "Should we use K8s?"
        assert root.depth == 0
        assert root.status == NodeStatus.ACTIVE
        assert dt.root is root


class TestCanFork:
    def test_can_fork_at_root(self):
        dt = DecisionTree(DiscussionConfig(max_tree_depth=3, max_tree_width=3))
        root = dt.create_root("q")
        assert dt.can_fork(root)

    def test_cannot_fork_at_max_depth(self):
        dt = DecisionTree(DiscussionConfig(max_tree_depth=1))
        root = dt.create_root("q")
        child = dt.add_child(root, "sub-q")
        assert not dt.can_fork(child)  # depth 1 == max_tree_depth

    def test_cannot_fork_at_max_width(self):
        dt = DecisionTree(DiscussionConfig(max_tree_width=2))
        root = dt.create_root("q")
        dt.add_child(root, "sub-1")
        dt.add_child(root, "sub-2")
        assert not dt.can_fork(root)  # 2 children == max_tree_width


class TestAddChild:
    def test_adds_child(self):
        dt = DecisionTree(DiscussionConfig())
        root = dt.create_root("q")
        child = dt.add_child(root, "sub-q")
        assert child.question == "sub-q"
        assert child.depth == 1
        assert child.parent_id == root.id
        assert len(root.children) == 1
        assert root.children[0] is child

    def test_raises_on_limit(self):
        dt = DecisionTree(DiscussionConfig(max_tree_width=1))
        root = dt.create_root("q")
        dt.add_child(root, "sub-1")
        with pytest.raises(ValueError, match="Cannot fork"):
            dt.add_child(root, "sub-2")


class TestFindNode:
    def test_find_root(self):
        dt = DecisionTree(DiscussionConfig())
        root = dt.create_root("q")
        assert dt.find_node(root.id) is root

    def test_find_child(self):
        dt = DecisionTree(DiscussionConfig())
        root = dt.create_root("q")
        child = dt.add_child(root, "sub")
        assert dt.find_node(child.id) is child

    def test_find_deep(self):
        dt = DecisionTree(DiscussionConfig(max_tree_depth=5))
        root = dt.create_root("q")
        c1 = dt.add_child(root, "c1")
        c2 = dt.add_child(c1, "c2")
        c3 = dt.add_child(c2, "c3")
        assert dt.find_node(c3.id) is c3

    def test_find_missing(self):
        dt = DecisionTree(DiscussionConfig())
        dt.create_root("q")
        assert dt.find_node("nonexistent") is None

    def test_find_empty_tree(self):
        dt = DecisionTree(DiscussionConfig())
        assert dt.find_node("x") is None


class TestGetContext:
    def test_root_no_context(self):
        dt = DecisionTree(DiscussionConfig())
        root = dt.create_root("q")
        assert dt.get_context_for_node(root) == ""

    def test_child_gets_parent_verdict(self):
        dt = DecisionTree(DiscussionConfig())
        root = dt.create_root("main")
        root.verdict = Verdict(
            summary="use K8s",
            confidence="high",
            key_facts=[], key_risks=[], key_values=[],
            mitigations=[], intuition_summary="", blue_hat_ruling="",
            next_actions=[],
        )
        child = dt.add_child(root, "which distro?")
        context = dt.get_context_for_node(child)
        assert "use K8s" in context
        assert "父结论" in context

    def test_sibling_conclusions(self):
        dt = DecisionTree(DiscussionConfig())
        root = dt.create_root("main")
        c1 = dt.add_child(root, "sub-1")
        c1.verdict = Verdict(
            summary="conclusion 1", confidence="medium",
            key_facts=[], key_risks=[], key_values=[],
            mitigations=[], intuition_summary="", blue_hat_ruling="",
            next_actions=[],
        )
        c1.status = NodeStatus.CONVERGED
        c2 = dt.add_child(root, "sub-2")
        context = dt.get_context_for_node(c2)
        assert "conclusion 1" in context
        assert "兄弟结论" in context


class TestAllNodes:
    def test_all_dfs(self):
        dt = DecisionTree(DiscussionConfig(max_tree_depth=3))
        root = dt.create_root("q")
        c1 = dt.add_child(root, "c1")
        c2 = dt.add_child(root, "c2")
        c1_1 = dt.add_child(c1, "c1_1")
        all_nodes = dt.all_nodes()
        assert len(all_nodes) == 4
        assert all_nodes[0] is root
        assert all_nodes[1] is c1
        assert all_nodes[2] is c1_1
        assert all_nodes[3] is c2

    def test_empty_tree(self):
        dt = DecisionTree(DiscussionConfig())
        assert dt.all_nodes() == []


class TestActiveNodes:
    def test_filters_active(self):
        dt = DecisionTree(DiscussionConfig())
        root = dt.create_root("q")
        c1 = dt.add_child(root, "c1")
        c1.status = NodeStatus.CONVERGED
        c2 = dt.add_child(root, "c2")
        active = dt.active_nodes()
        assert root in active
        assert c2 in active
        assert c1 not in active
