# -*- coding:Utf-8 -*-


from typing import Dict, Any, Optional, List


class Node:
    def __init__(self, value: Optional[Any]=None) -> None:
        self.children: Dict[str, Node] = {}
        self.value = value

    def __repr__(self):
        return f'{self.value}:{self.children}'
                            
def find(node: Node, key: str) -> str:
    """Find value by key in node."""
    for char in key:
        if char in node.children:
            node = node.children[char]
        else:
            raise KeyError(f'{key} is not in this tree')
    return node.value

def insert(node: Node, key: str, value: Any) -> None:
    """Insert key/value pair into node."""
    for char in key:
        if char not in node.children:
            node.children[char] = Node()
        node = node.children[char]
    node.value = value

def keys_with_prefix(root: Node, prefix: str, limit: int = 99999999) -> List[str]:
    results: List[str] = []
    x = get_node(root, prefix)
    _collect(x, list(prefix), results, limit)
    return results

def _collect(x: Optional[Node], prefix: List[str], results: List[str], limit: int) -> None:
    """
    Append keys under node `x` matching the given prefix to `results`.
    prefix: list of characters
    """
    if x is None:
        return
    if x.value is not None:
        if len(results) == limit:
            return
        prefix_str = ''.join(prefix)
        results.append(prefix_str)
    for c in x.children:
        prefix.append(c)
        _collect(x.children[c], prefix, results, limit)
        prefix.pop()  # delete last character
        
def get_node(node: Node, key: str) -> Optional[Node]:
    """
    Find node by key. This is the same as the `find` function defined above,
    but returning the found node itself rather than the found node's value.
    """
    for char in key:
        if char in node.children:
            node = node.children[char]
        else:
            return None
    return node

def get_tree(filename: str) -> Node:
    tree = Node()
    with open(filename, 'r', encoding='utf8') as datafile:
        data: List[str] = list(datafile)
        
    for word in data:
        insert(tree, word[:-1].lower(), 0)

    return tree


