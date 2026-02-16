import ctypes
import math
import uuid

from pycfb.constants import (
    HEADER_DIFAT_COUNT,
    SHIFT_MINISECTOR_BITS,
    SHIFT_SECTOR_BITS_V3,
    SIZE_DIFAT_ENTRY_BYTES,
    SIZE_DIRECTORY_ENTRY_BYTES,
    SIZE_FAT_ENTRY_BYTES,
    SIZE_MINISTREAM_CUTOFF_BYTES
)
from pycfb.enums import Sector
from pycfb.types import (
    DifatSector,
    DirEntry,
    FatSector,
    Header
)
from pycfb.util import get_unique_subdirs

class CFBContext:
    def __init__(
        self,
        stream_paths: list[str],
        stream_data: list[bytes],
        root_clsid: uuid.UUID
    ):
        self.stream_paths = stream_paths
        self.stream_data = stream_data
        self.root_clsid = root_clsid

        # Calculate sector sizes
        self.sector_size_bytes = 2**(SHIFT_SECTOR_BITS_V3)
        self.minisector_size_bytes = 2**(SHIFT_MINISECTOR_BITS)
        self.fat_entries_per_sector = self.sector_size_bytes // SIZE_FAT_ENTRY_BYTES
        self.difat_entries_per_sector = (self.sector_size_bytes // SIZE_DIFAT_ENTRY_BYTES) - 1

        self.data: bytearray
        self.ministream_data: bytearray

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

    def calc_total_size_bytes(self) -> int:
        total_sectors = 1 # Header
        total_sectors += self.calc_difat_size_sectors()
        total_sectors += self.calc_fat_size_sectors()
        total_sectors += self.calc_dir_size_sectors()
        total_sectors += self.calc_file_size_sectors()
        total_sectors += self.calc_minifat_size_sectors()
        total_sectors += math.ceil(self.calc_ministream_size_bytes()/self.sector_size_bytes)
        return total_sectors * self.sector_size_bytes

    def inc_next_freesect(self):
        # Used to track the next available free sector in the file
        self.next_freesect_number += 1
        self.next_freesect_offset += self.sector_size_bytes

    def inc_next_fat(self):
        # Used to track the next available FAT entry in the file
        self.next_fat += 1

    def inc_next_minifat(self):
        # Used to track the next available MINIFAT entry in the file
        self.next_minifat += 1

    def inc_next_directory(self):
        # Used to track the next available directory entry in a sector
        self.next_directory += SIZE_DIRECTORY_ENTRY_BYTES
        if (self.next_directory % self.sector_size_bytes) == 0:
            self.next_directory = 0
            self.fat_mgr.update(self.next_fat, self.next_freesect_offset // self.sector_size_bytes)
            self.inc_next_fat()
            self.inc_next_freesect()
            self.fat_mgr.update(self.next_fat, Sector.ENDOFCHAIN)

    def get_sector_offset(self, sector: ctypes.Structure) -> int:
        base_address = ctypes.addressof(ctypes.c_char.from_buffer(self.data))
        sector_address = ctypes.addressof(sector)
        return sector_address - base_address

    def get_sector_number(self, sector: ctypes.Structure) -> int:
        sector_offset = self.get_sector_offset(sector)
        sector_number = (sector_offset // self.sector_size_bytes) - 1
        return sector_number

    def calc_difat_size_entries(self) -> int:
        return self.calc_fat_size_sectors() + 1 # Add one for end-of-chain ???

    def calc_difat_size_sectors(self) -> int:
        # The DIFAT needs to allocate space for the FAT if it exceeds the 109
        # entries available in the header
        difat_entries = self.calc_difat_size_entries()
        difat_size_bytes = (difat_entries - HEADER_DIFAT_COUNT) * SIZE_DIFAT_ENTRY_BYTES
        difat_size_bytes = max(difat_size_bytes, 0)
        difat_size_sectors = math.ceil(difat_size_bytes / self.sector_size_bytes)
        return difat_size_sectors

    def calc_fat_size_entries(self) -> int:
        # The FAT needs to allocate space for the directory and each file
        # including end-of-chains for each
        fat_entries = self.calc_dir_size_sectors() + 1 # Add one for end-of-chain ???
        for x in self.calc_file_size_sectors_byfile():
            fat_entries += x + 1 # Add one for each end-of-chain

        # Include overhead for the FAT sectors themselves
        fat_entries += (fat_entries // self.fat_entries_per_sector)
        return fat_entries

    def calc_fat_size_sectors(self) -> int:
        fat_entries = self.calc_fat_size_entries()
        fat_size_bytes = fat_entries * SIZE_FAT_ENTRY_BYTES
        fat_size_sectors = math.ceil(fat_size_bytes / self.sector_size_bytes)
        return fat_size_sectors

    def calc_dir_size_entries(self) -> int:
        # The directory tree includes a Root Entry, one entry for each file, and one entry for each folder.
        file_count = len(self.stream_paths)
        folder_count = len(get_unique_subdirs(self.stream_paths))
        return file_count + folder_count + 1 # Adding one for Root Directory

    def calc_dir_size_sectors(self) -> int:
        directory_size_bytes = self.calc_dir_size_entries() * SIZE_DIRECTORY_ENTRY_BYTES
        directory_size_sectors = math.ceil(directory_size_bytes / self.sector_size_bytes)
        return directory_size_sectors

    def calc_file_size_sectors_byfile(self) -> list[int]:
        sectors = []
        for stream in self.stream_data:
            # Storage
            if stream is None:
                continue

            if len(stream) >= SIZE_MINISTREAM_CUTOFF_BYTES:
                sectors.append(math.ceil(len(stream)/self.sector_size_bytes))
            else:
                sectors.append(0)
        return sectors

    def calc_file_size_sectors(self) -> int:
        return sum(self.calc_file_size_sectors_byfile())

    def calc_file_size_minisectors_byfile(self) -> list[int]:
        sectors = []
        for stream in self.stream_data:
            # Storage
            if stream is None:
                continue

            if len(stream) < SIZE_MINISTREAM_CUTOFF_BYTES:
                sectors.append(math.ceil(len(stream)/self.minisector_size_bytes))
            else:
                sectors.append(0)
        return sectors

    def calc_ministream_size_minisectors(self) -> int:
        return sum(self.calc_file_size_minisectors_byfile())

    def calc_ministream_size_bytes(self) -> int:
        return self.calc_ministream_size_minisectors() * self.minisector_size_bytes

    def calc_minifat_size_sectors(self) -> int:
        return math.ceil(self.calc_ministream_size_minisectors() * SIZE_FAT_ENTRY_BYTES/self.sector_size_bytes)
