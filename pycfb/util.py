import os
from pathlib import Path

from pycfb.types import *

def GetUniqueSubdirs(paths: list[str]) -> list[str]:
    all_levels = set()
    for p in paths:
        for ancestor in Path(p).parents:
            ancestor_str = str(ancestor)
            # Filter out both the root and the current directory indicator
            if ancestor_str not in ('.', '/'):
                all_levels.add(ancestor_str)
    return sorted(list(all_levels))

def GetFileTree(paths: List[str]) -> List[FileTreeItem]:
    visited = {}
    
    # 1. Deconstruct paths and identify all unique segments
    for idx, path in enumerate(paths):
        path = os.path.normpath(path)
        parts = path.split(os.sep)
        
        for i in range(1, len(parts) + 1):
            segment = os.path.join(*parts[:i])
            is_last_part = (i == len(parts))
            
            if segment not in visited:
                name = os.path.basename(segment)
                is_file = is_last_part and ("." in name)
                visited[segment] = FileTreeItem(
                    path=segment,
                    name=name,
                    is_file=is_file,
                    original_index=idx if is_last_part else None
                )

    sorted_items = sorted(
        visited.values(), 
        key=lambda x: (x.path.count(os.sep), x.path)
    )
    path_to_final_idx = {item.path: i for i, item in enumerate(sorted_items)}

    for item in sorted_items:
        parent_path = os.path.dirname(item.path)
        if parent_path and parent_path != item.path and parent_path in path_to_final_idx:
            item.parent_index = path_to_final_idx[parent_path]

    return sorted_items