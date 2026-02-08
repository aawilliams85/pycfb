from pathlib import Path

def GetUniqueSubdirs(paths: list[str]) -> list[str]:
    all_levels = set()
    for p in paths:
        for ancestor in Path(p).parents:
            ancestor_str = str(ancestor)
            # Filter out both the root and the current directory indicator
            if ancestor_str not in ('.', '/'):
                all_levels.add(ancestor_str)
    return sorted(list(all_levels))