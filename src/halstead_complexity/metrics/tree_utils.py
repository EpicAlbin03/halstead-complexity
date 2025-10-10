from __future__ import annotations

from collections.abc import Iterator

from tree_sitter import Node, Tree


def iter_nodes(tree: Tree) -> Iterator[Node]:
    """Yield every node in tree using an explicit cursor walk.

    Args:
        tree: The tree-sitter Tree to traverse

    Yields:
        Each Node in the tree
    """
    cursor = tree.walk()
    visited_children = False
    while True:
        node = cursor.node
        if node is None:
            return
        yield node

        if not visited_children and cursor.goto_first_child():
            visited_children = False
            continue

        visited_children = True
        while not cursor.goto_next_sibling():
            if not cursor.goto_parent():
                return
        visited_children = False


def iter_leaf_nodes(tree: Tree) -> Iterator[Node]:
    """Yield only the leaf nodes in tree.

    Args:
        tree: The tree-sitter Tree to traverse

    Yields:
        Each leaf Node (nodes with no children) in the tree
    """
    for node in iter_nodes(tree):
        if node.child_count == 0:
            yield node
