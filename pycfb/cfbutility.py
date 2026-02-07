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
        self._fat_entries_per_sector = (self._sector_size_bytes // SIZE_FAT_ENTRY_BYTES)
        self._difat_entries_per_sector = (self._sector_size_bytes // SIZE_DIFAT_ENTRY_BYTES) - 1
        self._next_freesect_offset = 0x00000000
        self._next_freesect_number = 0

        ###########################################################################
        # Initialize binary structure            
        ###########################################################################
        self._data = bytearray(self._calc_total_size_bytes())

        # Header
        self._header = cHeader.from_buffer(self._data, self._next_freesect_offset)
        self._allocate_cfat_sectors()
        self._allocate_cdifat_sectors()

        self._header.signature = HEADER_SIGNATURE
        #self._header.clsid = HEADER_CLSID_NULL
        self._header.version_minor = HEADER_VERSION_MINOR
        self._header.version_major = HEADER_VERSION_MAJOR
        self._header.byte_order = HEADER_BYTE_ORDER
        self._header.sector_shift = SHIFT_SECTOR_BITS_V3
        self._header.mini_sector_shift = SHIFT_MINISECTOR_BITS
        self._header.sector_count_directory = 0 # Always zero for v3
        self._header.sector_count_fat = self._calc_size_fat_sectors()
        self._header.sector_start_directory = 0 # **** NEED TO POPULATE ***
        self._header.transaction_signature = 0
        self._header.mini_cutoff_size = SIZE_MINISTREAM_CUTOFF_BYTES
        self._header.sector_start_minifat = CfbSector.EndOfChain # not supporting MINISTREAM initially so MINIFAT is not needed
        self._header.sector_count_minifat = self._calc_size_minifat_sectors()

        if (len(self._cdifat_sectors) > 0):
            self._header.sector_start_difat = self._get_sector_offset(self._cdifat_sectors[0])
            self._header.sector_count_difat = len(self._cdifat_sectors)
        else:
            self._header.sector_start_difat = CfbSector.EndOfChain # Until DIFAT needs to be expanded, it ends with the header entries
            self._header.sector_count_difat = 0
        self._header.sector_data_difat[:] = self._init_table_entries(size=HEADER_DIFAT_COUNT)
        self._increment_next_freesect()

        # Create Root Directory entry
        self._root_directory = CfbDirEntry(
            name='Root Entry',
            name_len_bytes=22,
            type=CfbDirType.RootStorage,
            color=CfbDirColor.Red,
            sibling_id_left=CfbSector.FreeSect,
            sibling_id_right=CfbSector.FreeSect,
            child_id=CfbSector.EndOfChain, # not supporting MINISTREAM initially, which would typically be pointed here
            clsid=root_clsid,
            state=0,
            time_created=0,
            time_modified=0,
            sector_start=0,
            size_bytes=0
        )

        '''
        for stream in self._raw_input_data:
            stream_size_sectors = math.ceil(len(stream)/self._sector_size_bytes)
            for x in range(stream_size_sectors):
                stream_chunk_start = x * self._sector_size_bytes
                stream_chunk_end = (x + 1) * self._sector_size_bytes
                stream_chunk = stream[stream_chunk_start:stream_chunk_end]

                raw_chunk_start = self._next_freesect_offset
                raw_chunk_end = self._next_freesect_offset + self._sector_size_bytes
                self._data[raw_chunk_start:raw_chunk_end] = stream_chunk

                self._next_freesect_number += 1
                self._next_freesect_offset += self._sector_size_bytes
        '''

    def _init_sector(self, size: int) -> bytes: return bytes(self._sector_size_bytes)
    def _init_table_entries(self, size: int, value: int = CfbSector.FreeSect) -> list[int]: return [value] * size
    def _increment_next_freesect(self):
        self._next_freesect_number += 1
        self._next_freesect_offset += self._sector_size_bytes

    def _calc_total_size_bytes(self) -> int:
        total_sectors = 1 # Header
        total_sectors += self._calc_size_difat_sectors()
        total_sectors += self._calc_size_fat_sectors()
        total_sectors += self._calc_size_directory_sectors()
        total_sectors += self._calc_size_file_sectors()
        total_sectors += self._calc_size_minifat_sectors()
        total_sectors += self._calc_size_ministream_sectors()
        return (total_sectors * self._sector_size_bytes)
    
    def _get_sector_offset(self, sector: ctypes.Structure) -> int:
        base_address = ctypes.addressof(ctypes.c_char.from_buffer(self._data))
        sector_address = ctypes.addressof(sector)
        return (sector_address - base_address)

    ###########################################################################
    # DIFAT Logic
    ###########################################################################
    def _calc_size_difat_entries(self) -> int:
        return self._calc_size_fat_sectors() + 1 # Add one for end-of-chain ???
    def _calc_size_difat_sectors(self) -> int:
        # The DIFAT needs to allocate space for the FAT if it exceeds the 109 entries available in the header
        difat_entries = self._calc_size_difat_entries()
        difat_size_bytes = (difat_entries - HEADER_DIFAT_COUNT) * SIZE_DIFAT_ENTRY_BYTES
        if (difat_size_bytes < 0): difat_size_bytes = 0
        difat_size_sectors = math.ceil(difat_size_bytes / self._sector_size_bytes)
        return difat_size_sectors
    def _allocate_difat_sectors(self):
        # Initialize DIFAT list of entries
        self._difat_sectors: list[CfbMappedSector] = []

        # The first DIFAT sector is special because it is part of the header
        new_sector = CfbMappedSector(sector_size=(HEADER_DIFAT_COUNT * SIZE_DIFAT_ENTRY_BYTES), sector_number=-1,sector_offset=(-1*self._sector_size_bytes))
        new_sector.init_int32(value=CfbSector.FreeSect,length=HEADER_DIFAT_COUNT)
        self._difat_sectors.append(new_sector)

        # Subsequent DIFAT sectors are only created if necessary
        for x in range(self._calc_size_difat_sectors()):
            new_sector = CfbMappedSector(sector_size=self._sector_size_bytes, sector_number=self._next_freesect_number, sector_offset=self._next_freesect_offset)
            new_sector.init_int32(value=CfbSector.FreeSect,length=(self._sector_size_bytes // SIZE_FAT_ENTRY_BYTES))
            self._difat_sectors.append(new_sector)
            self._update_fat_entry(index=new_sector.sector_number, value=CfbSector.DifSect)
            self._next_freesect_offset += self._sector_size_bytes
            self._next_freesect_number += 1

    def _update_difat_entry(self, index: int, value: int):
        eps = self._sector_size_bytes // SIZE_DIFAT_ENTRY_BYTES
        sector_idx = index // eps
        sector_offset = (index % eps) * SIZE_DIFAT_ENTRY_BYTES
        self._difat_sectors[sector_idx].set_int32(offset=sector_offset,value=value)
    def _allocate_cdifat_sectors(self):
        self._cdifat_sectors: list[cDifatSector] = []
        for x in range(self._calc_size_difat_sectors()):
            new_sector = cDifatSector.from_buffer(self._data, self._next_freesect_offset)
            for y in range(self._difat_entries_per_sector): new_sector.entries[y] = CfbSector.FreeSect
            new_sector.next_difat = CfbSector.EndOfChain

            # Chain the previous DIFAT sector to this one
            if (x > 0): self._cdifat_sectors[x-1].next_difat = self._next_freesect_offset - self._sector_size_bytes

            self._cdifat_sectors.append(new_sector)
            # Set DIFAT entry in FAT?
            self._increment_next_freesect()
    def _update_cdifat_entry(self, index: int, value: int):
        if (index < HEADER_DIFAT_COUNT):
            print(f'Setting DIFAT {index} to {value} at header {index}')
            self._header.sector_data_difat[index] = value
        else:
            index_remainder = index - HEADER_DIFAT_COUNT
            sector_idx = index_remainder // self._difat_entries_per_sector
            entry_idx = index_remainder % self._difat_entries_per_sector
            print(f'Setting DIFAT {index} to {value} at {sector_idx} {entry_idx}')



    ###########################################################################
    # FAT Logic
    ###########################################################################
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
    def _allocate_cfat_sectors(self):
        self._cfat_sectors: list[cFatSector] = []
        for x in range(self._calc_size_fat_sectors()):
            new_sector = cFatSector.from_buffer(self._data, self._next_freesect_offset)
            for y in range(self._fat_entries_per_sector): new_sector.entries[y] = CfbSector.FreeSect
            self._cfat_sectors.append(new_sector)
            self._update_cfat_entry(x,CfbSector.FatSect)
            self._increment_next_freesect()
    def _update_cfat_entry(self, index: int, value: int):
        sector_idx = index // self._fat_entries_per_sector
        entry_idx = index % self._fat_entries_per_sector
        print(f'Setting FAT {index} to {value} at {sector_idx} {entry_idx}')
        self._cfat_sectors[sector_idx].entries[entry_idx] = value

    def _allocate_fat_sectors(self):
        self._fat_sectors: list[CfbMappedSector] = []
        for x in range(self._calc_size_fat_sectors()):
            new_sector = CfbMappedSector(sector_size=self._sector_size_bytes, sector_number=self._next_freesect_number, sector_offset=self._next_freesect_offset)
            new_sector.init_int32(value=CfbSector.FreeSect,length=(self._sector_size_bytes // SIZE_FAT_ENTRY_BYTES))
            self._fat_sectors.append(new_sector)
            self._update_fat_entry(index=new_sector.sector_number, value=CfbSector.FatSect)
            self._next_freesect_offset += self._sector_size_bytes
            self._next_freesect_number += 1
    def _update_fat_entry(self, index: int, value: int):
        eps = self._sector_size_bytes // SIZE_FAT_ENTRY_BYTES
        sector_idx = index // eps
        sector_offset = (index % eps) * SIZE_FAT_ENTRY_BYTES
        self._fat_sectors[sector_idx].set_int32(offset=sector_offset,value=value)
    def _fat_get_next_freesect(self) -> tuple[int,int]:
        eps = self._sector_size_bytes // SIZE_FAT_ENTRY_BYTES
        for x in self._fat_sectors:
            next_freesect_offset = x.seek_int32(CfbSector.FreeSect)
            if (next_freesect_offset >= 0):
                pass
                #sector_idx = 
                #sector_idx = index // eps
        raise ValueError('Failed to find next free sector in FAT.')

    ###########################################################################
    # Directory Logic
    ###########################################################################
    def _calc_size_directory_sectors(self) -> int:
        # The directory tree includes a Root Entry, one entry for each file, and one entry for each folder.
        file_count = len(self._raw_input_names)
        folder_count = len(GetUniqueSubdirs(self._raw_input_names))
        directory_size_bytes = (file_count + folder_count + 1) * SIZE_DIRECTORY_ENTRY_BYTES # Adding one for Root Directory
        directory_size_sectors = math.ceil(directory_size_bytes / self._sector_size_bytes)
        return directory_size_sectors

    ###########################################################################
    # User File Logic
    ###########################################################################
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
    def _write_stream(self, stream_data: bytes):
        stream_size_sectors = math.ceil(len(stream_data)/self._sector_size_bytes)
        for x in range(stream_size_sectors):
            
            stream_chunk_start = x * self._sector_size_bytes
            stream_chunk_end = (x + 1) * self._sector_size_bytes
            stream_chunk = stream_data[stream_chunk_start:stream_chunk_end]

            raw_chunk_start = self._next_freesect_offset
            raw_chunk_end = self._next_freesect_offset + self._sector_size_bytes
            self._data[raw_chunk_start:raw_chunk_end] = stream_chunk

            self._next_freesect_number += 1
            self._next_freesect_offset += self._sector_size_bytes