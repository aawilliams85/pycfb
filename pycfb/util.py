from pathlib import Path

def GetUniqueSubdirs(paths: list[str]) -> list[str]:
    all_levels = set()
    for p in paths:
        for ancestor in Path(p).parents:
            if str(ancestor) != '/': # Ignore the root if desired
                all_levels.add(str(ancestor))
    return sorted(list(all_levels))