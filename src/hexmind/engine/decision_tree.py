"""DecisionTree: manage tree nodes with depth/width limits and FORK logic."""

from __future__ import annotations

from hexmind.models.config import DiscussionConfig
from hexmind.models.tree import NodeStatus, TreeNode


class DecisionTree:
    """Manages a tree of discussion nodes (root = main question, children = sub-questions).

    Enforces:
    - max_tree_depth: no forking beyond this depth
    - max_tree_width: max children per node
    """

    def __init__(self, config: DiscussionConfig) -> None:
        self.config = config
        self.root: TreeNode | None = None

    def create_root(self, question: str) -> TreeNode:
        """Create and set the root node."""
        self.root = TreeNode(question=question, depth=0)
        return self.root

    def can_fork(self, node: TreeNode) -> bool:
        """Check if a node can create a new sub-question."""
        if node.depth >= self.config.max_tree_depth:
            return False
        if len(node.children) >= self.config.max_tree_width:
            return False
        return True

    def add_child(self, parent: TreeNode, sub_question: str) -> TreeNode:
        """Create a child node under parent. Raises if limits exceeded."""
        if not self.can_fork(parent):
            raise ValueError(
                f"Cannot fork: depth={parent.depth}/{self.config.max_tree_depth}, "
                f"children={len(parent.children)}/{self.config.max_tree_width}"
            )
        child = TreeNode(
            question=sub_question,
            depth=parent.depth + 1,
            parent_id=parent.id,
        )
        parent.children.append(child)
        return child

    def find_node(self, node_id: str) -> TreeNode | None:
        """Find a node by ID (DFS)."""
        if self.root is None:
            return None
        return self._find_recursive(self.root, node_id)

    def get_context_for_node(self, node: TreeNode) -> str:
        """Build context string: parent verdict summaries + existing child conclusions."""
        parts: list[str] = []

        # Walk from root to this node's parent, collecting verdicts
        ancestors = self._get_ancestors(node)
        for ancestor in ancestors:
            if ancestor.verdict:
                parts.append(
                    f"[父结论 — {ancestor.question}]: {ancestor.verdict.summary}"
                )

        # Sibling conclusions (other children of the same parent)
        if node.parent_id:
            parent = self.find_node(node.parent_id)
            if parent:
                for sibling in parent.children:
                    if sibling.id != node.id and sibling.verdict:
                        parts.append(
                            f"[兄弟结论 — {sibling.question}]: {sibling.verdict.summary}"
                        )

        return "\n".join(parts)

    def all_nodes(self) -> list[TreeNode]:
        """Return all nodes in DFS order."""
        if self.root is None:
            return []
        result: list[TreeNode] = []
        self._collect_dfs(self.root, result)
        return result

    def active_nodes(self) -> list[TreeNode]:
        """Return all nodes with ACTIVE status."""
        return [n for n in self.all_nodes() if n.status == NodeStatus.ACTIVE]

    # ── Private helpers ────────────────────────────────────────

    @staticmethod
    def _find_recursive(node: TreeNode, node_id: str) -> TreeNode | None:
        if node.id == node_id:
            return node
        for child in node.children:
            found = DecisionTree._find_recursive(child, node_id)
            if found:
                return found
        return None

    def _get_ancestors(self, node: TreeNode) -> list[TreeNode]:
        """Return list of ancestors from root to parent (not including self)."""
        ancestors: list[TreeNode] = []
        current_id = node.parent_id
        while current_id:
            parent = self.find_node(current_id)
            if parent is None:
                break
            ancestors.append(parent)
            current_id = parent.parent_id
        ancestors.reverse()
        return ancestors

    @staticmethod
    def _collect_dfs(node: TreeNode, result: list[TreeNode]) -> None:
        result.append(node)
        for child in node.children:
            DecisionTree._collect_dfs(child, result)
