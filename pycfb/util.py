from collections import defaultdict
from dataclasses import dataclass
import os
from pathlib import Path
from typing import Optional

@dataclass
class FileTreeItem:
    path: str
    name: str
    is_file: bool
    original_index: Optional[int] = None
    parent_index: Optional[int] = None

def get_unique_subdirs(paths: list[str]) -> list[str]:
    all_levels = set()
    for p in paths:
        for ancestor in Path(p).parents:
            ancestor_str = str(ancestor)
            # Filter out both the root and the current directory indicator
            if ancestor_str not in ('.', '/'):
                all_levels.add(ancestor_str)
    return sorted(list(all_levels))

def get_file_tree(paths: list[str]) -> list[FileTreeItem]:
    visited = {}

    # Build segment dict
    for idx, path in enumerate(paths):
        path = os.path.normpath(path)
        parts = path.split(os.sep)
        for i in range(1, len(parts) + 1):
            segment = os.path.join(*parts[:i])
            is_last_part = i == len(parts)
            if segment not in visited:
                name = os.path.basename(segment)

                # Check if it's a file (only if it's the leaf node in paths)
                is_file = is_last_part and ("." in name)
                visited[segment] = FileTreeItem(
                    path=segment,
                    name=name,
                    is_file=is_file,
                    original_index=idx if is_last_part else None
                )

    # Map children
    children_map = defaultdict(list)
    roots = []
    for item in visited.values():
        parent_path = os.path.dirname(item.path)
        # If it has no parent or parent is '.', it's a top-level root
        if not parent_path or parent_path == item.path or parent_path == '.':
            roots.append(item)
        else:
            children_map[parent_path].append(item)

    # Flatten
    ordered_items = []
    def traverse(current_item):
        ordered_items.append(current_item)
        children = children_map.get(current_item.path, [])
        children.sort(key=lambda x: x.name.upper())
        for child in children:
            traverse(child)
    roots.sort(key=lambda x: x.name.upper())
    for r in roots:
        traverse(r)

    # Map parent index
    path_to_new_idx = {item.path: i for i, item in enumerate(ordered_items)}
    for item in ordered_items:
        parent_path = os.path.dirname(item.path)
        if parent_path in path_to_new_idx:
            item.parent_index = path_to_new_idx[parent_path]
        else:
            item.parent_index = None

    return ordered_items