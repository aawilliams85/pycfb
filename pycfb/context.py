import ctypes
import math
import uuid

from pycfb.constants import *
from pycfb.enums import *
from pycfb.types import *
from pycfb.util import *

class CFBContext:
    def __init__(
        self,
        stream_names: list[str],
        stream_paths: list[str],
        stream_data: list[bytes],
        root_clsid: uuid.UUID
    ):
        self.stream_names = stream_names
        self.stream_paths = stream_paths
        self.stream_data = stream_data
        self.root_clsid = root_clsid

        # Calculate sector sizes
        self.sector_size_bytes = 2**(SHIFT_SECTOR_BITS_V3)
        self.minisector_size_bytes = 2**(SHIFT_MINISECTOR_BITS)
        self.fat_entries_per_sector = self.sector_size_bytes // SIZE_FAT_ENTRY_BYTES
        self.difat_entries_per_sector = (self.sector_size_bytes // SIZE_DIFAT_ENTRY_BYTES) - 1

        self.data: bytearray
        self.minidata: bytearray

        self.header: Header = None
        self.header_mgr = None

        self.fat: list[FatSector] = []
        self.fat_mgr = None

        self.difat: list[DifatSector] = []
        self.difat_mgr = None

        self.directory: list[DirEntry] = []
        self.directory_mgr = None

        self.minifat: list[FatSector] = []
        self.minifat_mgr = None

        self.ministream_mgr = None
        self.ministream_start_minisectors: list[int] = [0] * len(self.stream_data)
        self.ministream_start = 0

        self.stream_mgr = None
        self.stream_start_sectors: list[int] = [0] * len(self.stream_data)

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

    def _increment_next_directory(self):
        # Used to track the next available directory entry in a sector
        self.next_directory += SIZE_DIRECTORY_ENTRY_BYTES
        if (self.next_directory % self.sector_size_bytes) == 0:
            self.next_directory = 0
            self.fat_mgr.update(self.next_fat, self.next_freesect_offset // self.sector_size_bytes)
            self._increment_next_fat()
            self._increment_next_freesect()
            self.fat_mgr.update(self.next_fat, Sector.ENDOFCHAIN)

    def _get_sector_offset(self, sector: ctypes.Structure) -> int:
        base_address = ctypes.addressof(ctypes.c_char.from_buffer(self.data))
        sector_address = ctypes.addressof(sector)
        return sector_address - base_address

    def _get_sector_number(self, sector: ctypes.Structure) -> int:
        sector_offset = self._get_sector_offset(sector)
        sector_number = (sector_offset // self.sector_size_bytes) - 1
        return sector_number

    def _calc_size_difat_entries(self) -> int:
        return self._calc_size_fat_sectors() + 1 # Add one for end-of-chain ???

    def _calc_size_difat_sectors(self) -> int:
        # The DIFAT needs to allocate space for the FAT if it exceeds the 109
        # entries available in the header
        difat_entries = self._calc_size_difat_entries()
        difat_size_bytes = (difat_entries - HEADER_DIFAT_COUNT) * SIZE_DIFAT_ENTRY_BYTES
        difat_size_bytes = max(difat_size_bytes, 0)
        difat_size_sectors = math.ceil(difat_size_bytes / self.sector_size_bytes)
        return difat_size_sectors

    def _calc_size_fat_entries(self) -> int:
        # The FAT needs to allocate space for the directory and each file, including end-of-chains for each
        fat_entries = self._calc_size_directory_sectors() + 1 # Add one for end-of-chain ???
        for x in self._calc_size_file_sectors_by_file(): fat_entries += (x + 1) # Add one for each end-of-chain
        fat_entries += (fat_entries // self.fat_entries_per_sector) # Include overhead for the FAT sectors
        return fat_entries

    def _calc_size_fat_sectors(self) -> int:
        fat_entries = self._calc_size_fat_entries()
        fat_size_bytes = fat_entries * SIZE_FAT_ENTRY_BYTES
        fat_size_sectors = math.ceil(fat_size_bytes / self.sector_size_bytes)
        return fat_size_sectors
    
    def _calc_size_directory_entries(self) -> int:
        # The directory tree includes a Root Entry, one entry for each file, and one entry for each folder.
        file_count = len(self.stream_names)
        folder_count = len(get_unique_subdirs(self.stream_paths))
        return (file_count + folder_count + 1) # Adding one for Root Directory

    def _calc_size_directory_sectors(self) -> int:
        directory_size_bytes = self._calc_size_directory_entries() * SIZE_DIRECTORY_ENTRY_BYTES
        directory_size_sectors = math.ceil(directory_size_bytes / self.sector_size_bytes)
        return directory_size_sectors
    
    def _calc_size_file_sectors_by_file(self) -> list[int]:
        sectors = []
        for stream in self.stream_data:
            if len(stream) >= SIZE_MINISTREAM_CUTOFF_BYTES:
                sectors.append(math.ceil(len(stream)/self.sector_size_bytes))
            else:
                sectors.append(0)
        return sectors

    def _calc_size_file_sectors(self) -> int:
        return sum(self._calc_size_file_sectors_by_file())
    
    def _calc_size_fat_entries(self) -> int:
        # The FAT needs to allocate space for the directory and each file, including end-of-chains for each
        fat_entries = self._calc_size_directory_sectors() + 1 # Add one for end-of-chain ???
        for x in self._calc_size_file_sectors_by_file(): fat_entries += (x + 1) # Add one for each end-of-chain
        fat_entries += (fat_entries // self.fat_entries_per_sector) # Include overhead for the FAT sectors
        return fat_entries

    def _calc_size_fat_sectors(self) -> int:
        fat_entries = self._calc_size_fat_entries()
        fat_size_bytes = fat_entries * SIZE_FAT_ENTRY_BYTES
        fat_size_sectors = math.ceil(fat_size_bytes / self.sector_size_bytes)
        return fat_size_sectors

    def _calc_size_ministream_sectors_by_file(self) -> list[int]:
        sectors = []
        for stream in self.stream_data:
            if len(stream) < SIZE_MINISTREAM_CUTOFF_BYTES:
                sectors.append(math.ceil(len(stream)/self.minisector_size_bytes))
            else:
                sectors.append(0)
        return sectors

    def _calc_size_ministream_sectors(self) -> int:
        return sum(self._calc_size_ministream_sectors_by_file())
    
    def _calc_ministream_size_bytes(self) -> int:
        return self._calc_size_ministream_sectors() * self.minisector_size_bytes

    def _calc_size_minifat_sectors(self) -> int:
        return math.ceil(self._calc_size_ministream_sectors() * SIZE_FAT_ENTRY_BYTES/self.sector_size_bytes)
