from collections import defaultdict
import math
import uuid

from pycfb.constants import *
from pycfb.context import CFBContext
from pycfb.enums import *
from pycfb.difat import CFBDifatMgr
from pycfb.directory import CFBDirectoryMgr
from pycfb.header import CFBHeaderMgr
from pycfb.fat import CFBFatMgr
from pycfb.minifat import CFBMinifatMgr
from pycfb.ministream import CFBMinistreamMgr
from pycfb.stream import CFBStreamMgr
from pycfb.types import *
from pycfb.util import *

VERBOSE = 0

class CFBWriter:
    def __init__(
        self,
        stream_names: list[str],
        stream_paths: list[str],
        stream_data: list[bytes],
        root_clsid: uuid.UUID
    ):
        # Ingest raw streams
        self._raw_input_names = stream_names
        self._raw_input_paths = stream_paths
        self._raw_input_data = stream_data
        self._root_clsid = root_clsid
        self.ctx = CFBContext(stream_names, stream_paths, stream_data, root_clsid)
        self.ctx.header_mgr = CFBHeaderMgr(self.ctx)
        self.ctx.fat_mgr = CFBFatMgr(self.ctx)
        self.ctx.minifat_mgr = CFBMinifatMgr(self.ctx)
        self.ctx.difat_mgr = CFBDifatMgr(self.ctx)
        self.ctx.ministream_mgr = CFBMinistreamMgr(self.ctx)
        self.ctx.stream_mgr = CFBStreamMgr(self.ctx)
        self.ctx.directory_mgr = CFBDirectoryMgr(self.ctx)

        ###########################################################################
        # Initialize binary structure
        ###########################################################################
        self.ctx.data = bytearray(self._calc_total_size_bytes())
        self.ctx.minidata = bytearray(self._calc_ministream_size_bytes())

        self.ctx.header_mgr.allocate()
        self.ctx.fat_mgr.allocate()
        self.ctx.minifat_mgr.allocate()
        self.ctx.difat_mgr.allocate()
        self.ctx.difat_mgr.update()
        self.ctx.ministream_mgr.allocate()
        self.ctx.stream_mgr.allocate()
        self.ctx.directory_mgr.allocate()
        self.ctx.header_mgr.update()

    @property
    def data(self):
        return self.ctx.data

    def _increment_next_freesect(self):
        # Used to track the next available free sector in the file
        self.ctx.next_freesect_number += 1
        self.ctx.next_freesect_offset += self.ctx.sector_size_bytes

    def _increment_next_fat(self):
        # Used to track the next available FAT entry in the file
        self.ctx.next_fat += 1

    def _increment_next_minifat(self):
        # Used to track the next available MINIFAT entry in the file
        self.ctx.next_minifat += 1

    def _increment_next_directory(self):
        # Used to track the next available directory entry in a sector
        self.ctx.next_directory += SIZE_DIRECTORY_ENTRY_BYTES
        if (self.ctx.next_directory % self.ctx.sector_size_bytes) == 0:
            self.ctx.next_directory = 0
            self.ctx.fat_mgr.update(self.ctx.next_fat, self.ctx.next_freesect_offset // self.ctx.sector_size_bytes)
            self._increment_next_fat()
            self._increment_next_freesect()
            self.ctx.fat_mgr.update(self.ctx.next_fat, Sector.ENDOFCHAIN)

    def _calc_total_size_bytes(self) -> int:
        total_sectors = 1 # Header
        total_sectors += self._calc_size_difat_sectors()
        total_sectors += self._calc_size_fat_sectors()
        total_sectors += self._calc_size_directory_sectors()
        total_sectors += self._calc_size_file_sectors()
        total_sectors += self._calc_size_minifat_sectors()
        total_sectors += math.ceil(self._calc_ministream_size_bytes()/self.ctx.sector_size_bytes)
        return total_sectors * self.ctx.sector_size_bytes

    def _get_sector_offset(self, sector: ctypes.Structure) -> int:
        base_address = ctypes.addressof(ctypes.c_char.from_buffer(self.ctx.data))
        sector_address = ctypes.addressof(sector)
        return sector_address - base_address

    def _get_sector_number(self, sector: ctypes.Structure) -> int:
        sector_offset = self._get_sector_offset(sector)
        sector_number = (sector_offset // self.ctx.sector_size_bytes) - 1
        return sector_number

    ###########################################################################
    # Header Logic
    ###########################################################################


    ###########################################################################
    # DIFAT Logic
    ###########################################################################
    def _calc_size_difat_entries(self) -> int:
        return self._calc_size_fat_sectors() + 1 # Add one for end-of-chain ???

    def _calc_size_difat_sectors(self) -> int:
        # The DIFAT needs to allocate space for the FAT if it exceeds the 109
        # entries available in the header
        difat_entries = self._calc_size_difat_entries()
        difat_size_bytes = (difat_entries - HEADER_DIFAT_COUNT) * SIZE_DIFAT_ENTRY_BYTES
        difat_size_bytes = max(difat_size_bytes, 0)
        difat_size_sectors = math.ceil(difat_size_bytes / self.ctx.sector_size_bytes)
        return difat_size_sectors

    ###########################################################################
    # FAT Logic
    ###########################################################################
    def _calc_size_fat_entries(self) -> int:
        # The FAT needs to allocate space for the directory and each file, including end-of-chains for each
        fat_entries = self._calc_size_directory_sectors() + 1 # Add one for end-of-chain ???
        for x in self._calc_size_file_sectors_by_file(): fat_entries += (x + 1) # Add one for each end-of-chain
        fat_entries += (fat_entries // self.ctx.fat_entries_per_sector) # Include overhead for the FAT sectors
        return fat_entries

    def _calc_size_fat_sectors(self) -> int:
        fat_entries = self._calc_size_fat_entries()
        fat_size_bytes = fat_entries * SIZE_FAT_ENTRY_BYTES
        fat_size_sectors = math.ceil(fat_size_bytes / self.ctx.sector_size_bytes)
        return fat_size_sectors

    ###########################################################################
    # MINIFAT Logic
    ###########################################################################
    def _calc_size_ministream_sectors_by_file(self) -> list[int]:
        sectors = []
        for stream in self._raw_input_data:
            if len(stream) < SIZE_MINISTREAM_CUTOFF_BYTES:
                sectors.append(math.ceil(len(stream)/self.ctx.minisector_size_bytes))
            else:
                sectors.append(0)
        return sectors

    def _calc_size_ministream_sectors(self) -> int:
        return sum(self._calc_size_ministream_sectors_by_file())
    
    def _calc_ministream_size_bytes(self) -> int:
        return self._calc_size_ministream_sectors() * self.ctx.minisector_size_bytes

    def _calc_size_minifat_sectors(self) -> int:
        return math.ceil(self._calc_size_ministream_sectors() * SIZE_FAT_ENTRY_BYTES/self.ctx.sector_size_bytes)

    ###########################################################################
    # Directory Logic
    ###########################################################################
    def _calc_size_directory_entries(self) -> int:
        # The directory tree includes a Root Entry, one entry for each file, and one entry for each folder.
        file_count = len(self._raw_input_names)
        folder_count = len(get_unique_subdirs(self._raw_input_paths))
        return (file_count + folder_count + 1) # Adding one for Root Directory

    def _calc_size_directory_sectors(self) -> int:
        directory_size_bytes = self._calc_size_directory_entries() * SIZE_DIRECTORY_ENTRY_BYTES
        directory_size_sectors = math.ceil(directory_size_bytes / self.ctx.sector_size_bytes)
        #raise Exception(f'dir bytes {directory_size_bytes}, sectors {directory_size_sectors}')
        return directory_size_sectors

    ###########################################################################
    # User File Logic
    ###########################################################################
    def _calc_size_file_sectors_by_file(self) -> list[int]:
        sectors = []
        for stream in self._raw_input_data:
            if len(stream) >= SIZE_MINISTREAM_CUTOFF_BYTES:
                sectors.append(math.ceil(len(stream)/self.ctx.sector_size_bytes))
            else:
                sectors.append(0)
        return sectors

    def _calc_size_file_sectors(self) -> int:
        return sum(self._calc_size_file_sectors_by_file())

