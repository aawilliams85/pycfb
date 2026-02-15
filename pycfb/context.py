import ctypes
import uuid

from pycfb.constants import *
from pycfb.types import *

class CFBContext:
    def __init__(
        self,
        stream_names: list[str],
        stream_paths: list[str],
        stream_data: list[str],
        root_clsid: uuid.UUID
    ):
        self.stream_names = stream_names
        self.stream_paths = stream_paths
        self.stream_data = stream_data
        self.root_clsid = root_clsid

        # Calculate sector sizes
        self.sector_size_bytes = 2**(SHIFT_SECTOR_BITS_V3)
        self.sector_size_ministream_bytes = 2**(SHIFT_MINISECTOR_BITS)
        self.fat_entries_per_sector = self.sector_size_bytes // SIZE_FAT_ENTRY_BYTES
        self.difat_entries_per_sector = (self.sector_size_bytes // SIZE_DIFAT_ENTRY_BYTES) - 1

        self.data: bytearray
        self.minidata: bytearray

        self.header: Header = None
        self.header_mgr = None

        self.fat: FatSector = None
        self.fat_mgr = None

        self.difat: DifatSector = None
        self.difat_mgr = None

        self.directory: DirEntry = None
        self.directory_mgr = None

        self.minifat: FatSector = None
        self.minifat_mgr = None

        self.next_freesect_offset = 0x00000000
        self.next_freesect_number = 0
        self.next_fat = 0
        self.next_minifat = 0
        self.next_directory = 0

    def _increment_next_freesect(self):
        # Used to track the next available free sector in the file
        self.next_freesect_number += 1
        self.next_freesect_offset += self.sector_size_bytes

    def _increment_next_fat(self):
        # Used to track the next available FAT entry in the file
        self.next_fat += 1

    def _increment_next_minifat(self):
        # Used to track the next available MINIFAT entry in the file
        self.next_minifat += 1

    def _get_sector_offset(self, sector: ctypes.Structure) -> int:
        base_address = ctypes.addressof(ctypes.c_char.from_buffer(self.data))
        sector_address = ctypes.addressof(sector)
        return sector_address - base_address

    def _get_sector_number(self, sector: ctypes.Structure) -> int:
        sector_offset = self._get_sector_offset(sector)
        sector_number = (sector_offset // self.sector_size_bytes) - 1
        return sector_number