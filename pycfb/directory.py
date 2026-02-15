import math

from pycfb.constants import *
from pycfb.context import CFBContext
from pycfb.enums import DirColor, DirType, Sector
from pycfb.types import DirEntry
from pycfb.util import *

class CFBDirectoryMgr:
    def __init__(
        self,
        ctx: CFBContext
    ):
        self.ctx = ctx

    def allocate(self):
        self.ctx.next_directory = 0

        # Root Entry
        self.ctx.directory.append(self.allocate_root())
        self.ctx.fat_mgr.update(self.ctx.next_fat, Sector.ENDOFCHAIN)
        self.ctx._increment_next_directory()

        dirs = get_file_tree(self.ctx.stream_paths)
        
        # Storage and Stream entries
        for i, x in enumerate(dirs):
            raw_name = f'{x.name[:31]}\x00'.encode('utf-16-le')
            new_entry = DirEntry.from_buffer(self.ctx.data, self.ctx.next_freesect_offset + self.ctx.next_directory)
            
            new_entry.name[:len(raw_name)] = raw_name
            new_entry.name_len_bytes = len(raw_name)
            new_entry.object_type = DirType.STREAM if x.is_file else DirType.STORAGE
            new_entry.color_flag = DirColor.BLACK # To start
            new_entry.left_sibling_id = Sector.NOSTREAM
            new_entry.right_sibling_id = Sector.NOSTREAM
            new_entry.child_id = Sector.NOSTREAM
            
            if x.is_file:
                new_entry.size_bytes = len(self.ctx.stream_data[x.original_index])
                if new_entry.size_bytes >= SIZE_MINISTREAM_CUTOFF_BYTES:
                    new_entry.sector_start = self.ctx.stream_start_sectors[x.original_index] - 1
                else:
                    new_entry.sector_start = self.ctx.ministream_start_minisectors[x.original_index]
            else:
                new_entry.size_bytes = 0
                new_entry.sector_start = 0

            self.ctx.directory.append(new_entry)
            self.ctx._increment_next_directory()

        # Build tree hierarchy
        children_map = defaultdict(list)
        for i, x in enumerate(dirs):
            parent_idx = -1 if x.parent_index is None else x.parent_index
            children_map[parent_idx].append(i + 1)

        def build_balanced_tree(indices, color=DirColor.BLACK):
            """
            Recursively builds a balanced binary tree.
            Assigns Left/Right siblings and alternates Red/Black colors.
            """
            if not indices:
                return Sector.NOSTREAM
            
            # Sort by name length, then uppercase
            indices.sort(key=lambda idx: (len(dirs[idx-1].name), dirs[idx-1].name.upper()))            

            mid = len(indices) // 2
            current_node_idx = indices[mid]            
            node = self.ctx.directory[current_node_idx]
            node.color_flag = color
            
            # Build subtree
            next_color = DirColor.RED if color == DirColor.BLACK else DirColor.BLACK            
            node.left_sibling_id = build_balanced_tree(indices[:mid], next_color)
            node.right_sibling_id = build_balanced_tree(indices[mid+1:], next_color)
            
            return current_node_idx

        # Fix pointers
        for parent_idx, children in children_map.items():
            child_tree_root = build_balanced_tree(children, DirColor.BLACK)
            
            if parent_idx == -1:
                self.ctx.directory[0].child_id = child_tree_root
            else:
                self.ctx.directory[parent_idx + 1].child_id = child_tree_root

            self.ctx._increment_next_fat()
            self.ctx._increment_next_freesect()
            
    def allocate_root(self) -> DirEntry:
        raw_name = 'Root Entry\x00'.encode('utf-16-le')
        new_entry = DirEntry.from_buffer(self.ctx.data, self.ctx.next_freesect_offset + self.ctx.next_directory)
        new_entry.name[:len(raw_name)] = raw_name
        new_entry.name_len_bytes = len(raw_name)
        new_entry.object_type = DirType.ROOTSTORAGE
        new_entry.color_flag = DirColor.BLACK
        new_entry.left_sibling_id = Sector.NOSTREAM
        new_entry.right_sibling_id = Sector.NOSTREAM

        if len(self.ctx.minifat) > 0:
            new_entry.sector_start = self.ctx.ministream_start - 1
            new_entry.size_bytes = math.ceil(len(self.ctx.minidata)/self.ctx.sector_size_bytes) * self.ctx.sector_size_bytes

        new_entry.child_id = Sector.NOSTREAM
        new_entry.clsid = (ctypes.c_byte * 16).from_buffer_copy(self.ctx.root_clsid.bytes)
        return new_entry