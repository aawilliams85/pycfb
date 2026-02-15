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
    input_paths_set = {os.path.normpath(p) for p in paths}

    for idx, path in enumerate(paths):
        path = os.path.normpath(path)
        parts = path.split(os.sep)

        # Handle absolute paths or root segments
        if parts[0] == '' and path.startswith(os.sep):
            parts[0] = os.sep

        for i in range(1, len(parts) + 1):
            segment = os.path.join(*parts[:i])
            is_input_leaf = i == len(parts)

            if segment not in visited:
                name = os.path.basename(segment) or segment
                # If it's in the input list, it's a file; otherwise, it's a directory
                is_file = segment in input_paths_set

                visited[segment] = FileTreeItem(
                    path=segment,
                    name=name,
                    is_file=is_file,
                    original_index=idx if is_input_leaf else None
                )

    # Map children
    children_map = defaultdict(list)
    roots = []
    for item in visited.values():
        parent_path = os.path.dirname(item.path)
        if not parent_path or parent_path == item.path or parent_path == '.':
            roots.append(item)
        else:
            children_map[parent_path].append(item)

    # Flatten with specific sorting logic
    ordered_items = []
    def sort_key(item):
        # First element (is_file): False (0) for folders, True (1) for files
        # Second element: Case-insensitive name
        return (item.is_file, item.name.lower())

    def traverse(current_item):
        ordered_items.append(current_item)
        children = children_map.get(current_item.path, [])
        children.sort(key=sort_key)
        for child in children:
            traverse(child)

    roots.sort(key=sort_key)
    for r in roots:
        traverse(r)

    # Map parents to flat list
    path_to_new_idx = {item.path: i for i, item in enumerate(ordered_items)}
    for item in ordered_items:
        parent_path = os.path.dirname(item.path)
        item.parent_index = path_to_new_idx.get(parent_path)

    return ordered_items
