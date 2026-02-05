import math
import uuid

from pycfb.constants import *
from pycfb.enums import *
from pycfb.types import *
from pycfb.util import *

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

        # Calculate sector sizes
        self._sector_size_bytes = 2**(SHIFT_SECTOR_BITS_V3)
        self._sector_size_ministream_bytes = 2**(SHIFT_MINISECTOR_BITS)
        self._next_freesect_offset = 0x00000000
        self._next_freesect_number = 0

        # Initialize table entries
        #
        # 
        self._allocate_fat()
        print(self._fat_sectors)
        print(self._fat_sectors[0].hex_dump())
        self._difat_entries = self._init_table_entries(size=self._calc_size_difat_entries())
        self._fat_entries = self._init_table_entries(size=self._calc_size_fat_entries())

        # Keep in mind that the header is treated like "sector -1" even though it is
        # the beginning of the file.  So a directory starting at sector 1 is an offset
        # of 1024 bytes.
        self._header = CfbHeader(
            header_signature=HEADER_SIGNATURE,
            header_clsid=HEADER_CLSID_NULL,
            version_minor=HEADER_VERSION_MINOR,
            version_major=HEADER_VERSION_MAJOR,
            byte_order=HEADER_BYTE_ORDER,
            sector_shift=SHIFT_SECTOR_BITS_V3, # only targeting V3
            ministream_sector_shift=SHIFT_MINISECTOR_BITS,
            sector_count_directory=0, # always 0 for V3
            sector_count_fat=self._calc_size_fat_sectors(),
            sector_start_directory=1, # always 1
            transaction_signature_number=0,
            ministream_cutoff_size=SIZE_MINISTREAM_CUTOFF_BYTES,
            sector_start_minifat=CfbSector.EndOfChain, # not supporting MINISTREAM initially, so MINIFAT is not needed
            sector_count_minifat=self._calc_size_minifat_sectors(),
            sector_start_difat=CfbSector.EndOfChain, # until DIFAT needs to be expanded, it ends with the header entries
            sector_count_difat=self._calc_size_difat_sectors(),
            sector_data_difat=self._init_table_entries(size=HEADER_DIFAT_COUNT)
        )

        # Create Root Directory entry
        self._root_directory = CfbDirEntry(
            name='Root Entry',
            name_len_bytes=22,
            type=enums.CfbDirType.RootStorage,
            color=enums.CfbDirColor.Red,
            sibling_id_left=CfbSector.FreeSect,
            sibling_id_right=CfbSector.FreeSect,
            child_id=enums.CfbSector.EndOfChain, # not supporting MINISTREAM initially, which would typically be pointed here
            clsid=root_clsid,
            state=0,
            time_created=0,
            time_modified=0,
            sector_start=0,
            size_bytes=0
        )
        for stream in self._raw_input_data:
            pass

        print(self._header)
        print(self._root_directory)
        print(self._calc_size_directory_sectors())
        print(self._calc_size_file_sectors())
        print(self._calc_size_fat_sectors())
        print(self._calc_size_difat_sectors())

    def _init_sector(self, size: int) -> bytes: return bytes(self._sector_size_bytes)
    def _init_table_entries(self, size: int, value: int = CfbSector.FreeSect) -> list[int]: return [value] * size

    # DIFAT calculations
    #
    #
    def _calc_size_difat_entries(self) -> int:
        return self._calc_size_fat_sectors() + 1 # Add one for end-of-chain ???
    def _calc_size_difat_sectors(self) -> int:
        # The DIFAT needs to allocate space for the FAT if it exceeds the 109 entries available in the header
        difat_entries = self._calc_size_difat_entries()
        difat_size_bytes = (difat_entries - HEADER_DIFAT_COUNT) * SIZE_DIFAT_ENTRY_BYTES
        if (difat_size_bytes < 0): difat_size_bytes = 0
        difat_size_sectors = math.ceil(difat_size_bytes / self._sector_size_bytes)
        return difat_size_sectors
    def _allocate_difat(self):
        self._difat_sectors: list[CfbMappedSector] = []
        for x in range(self._calc_size_difat_sectors()):
            new_sector = CfbMappedSector(sector_size=self._sector_size_bytes, sector_number=self._next_freesect_number, sector_offset=self._next_freesect_offset)
            self._next_freesect_offset += self._sector_size_bytes
            self._next_freesect_number += 1
            self._difat_sectors.append(new_sector)
            # Still need to mark DIFSECT in corresponding FAT entry

    # FAT calculations
    #
    #
    def _calc_size_fat_entries(self) -> int:
        # The FAT needs to allocate space for the directory and each file, including end-of-chains for each
        fat_entries = self._calc_size_directory_sectors() + 1 # Add one for end-of-chain ???
        for x in self._calc_size_file_sectors_by_file(): fat_entries += (x + 1) # Add one for each end-of-chain
        return fat_entries
    def _calc_size_fat_sectors(self) -> int:
        fat_entries = self._calc_size_fat_entries()
        fat_size_bytes = fat_entries * SIZE_FAT_ENTRY_BYTES
        fat_size_sectors = math.ceil(fat_size_bytes / self._sector_size_bytes)
        return fat_size_sectors
    def _allocate_fat(self):
        self._fat_sectors: list[CfbMappedSector] = []
        for x in range(self._calc_size_fat_sectors()):
            new_sector = CfbMappedSector(sector_size=self._sector_size_bytes, sector_number=self._next_freesect_number, sector_offset=self._next_freesect_offset)
            self._fat_sectors.append(new_sector)
            self._update_fat(index=self._next_freesect_number, value=CfbSector.FatSect)
            self._next_freesect_offset += self._sector_size_bytes
            self._next_freesect_number += 1
    def _update_fat(self, index: int, value: int):
        eps = self._sector_size_bytes // SIZE_FAT_ENTRY_BYTES
        sector_idx = index // eps
        sector_offset = (index % eps) * SIZE_FAT_ENTRY_BYTES
        self._fat_sectors[sector_idx].set_int32(offset=sector_offset,value=value)

    # Directory calculations
    #
    #
    def _calc_size_directory_sectors(self) -> int:
        # The directory tree includes a Root Entry, one entry for each file, and one entry for each folder.
        file_count = len(self._raw_input_names)
        folder_count = len(GetUniqueSubdirs(self._raw_input_names))
        directory_size_bytes = (file_count + folder_count + 1) * SIZE_DIRECTORY_ENTRY_BYTES # Adding one for Root Directory
        directory_size_sectors = math.ceil(directory_size_bytes / self._sector_size_bytes)
        return directory_size_sectors

    # User file calcaulations
    #
    #
    def _calc_size_ministream_sectors(self) -> int:
        # Not supporting MINISTREAM initially
        return 0
    def _calc_size_minifat_sectors(self) -> int:
        # Not supporting MINIFAT initially
        return 0
    def _calc_size_file_sectors_by_file(self) -> list[int]:
        sectors = []
        for stream in self._raw_input_data: sectors.append(math.ceil(len(stream)/self._sector_size_bytes))
        return sectors
    def _calc_size_file_sectors(self) -> int:
        return sum(self._calc_size_file_sectors_by_file())
