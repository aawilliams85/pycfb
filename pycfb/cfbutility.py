import math
import uuid

from pycfb.constants import *
from pycfb.enums import *
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

        # Calculate sector sizes
        self._sector_size_bytes = 2**(SHIFT_SECTOR_BITS_V3)
        self._sector_size_ministream_bytes = 2**(SHIFT_MINISECTOR_BITS)
        self._fat_entries_per_sector = (self._sector_size_bytes // SIZE_FAT_ENTRY_BYTES)
        self._difat_entries_per_sector = (self._sector_size_bytes // SIZE_DIFAT_ENTRY_BYTES) - 1
        self._next_freesect_offset = 0x00000000
        self._next_freesect_number = 0
        self._next_fat = 0

        ###########################################################################
        # Initialize binary structure            
        ###########################################################################
        self._data = bytearray(self._calc_total_size_bytes())
        self._allocate_header()
        self._allocate_fat()
        self._allocate_minifat()
        self._allocate_difat()
        self._update_difat()

        self._stream_start_sectors: list[int] = []
        for stream in self._raw_input_data:
            self._stream_start_sectors.append(self._next_freesect_number)
            self._write_stream_to_fat(stream)

        self._allocate_directory()
        self._update_header()

    def _increment_next_freesect(self):
        # Used to track the next available free sector in the file
        self._next_freesect_number += 1
        self._next_freesect_offset += self._sector_size_bytes

    def _increment_next_fat(self):
        # Used to track the next available FAT entry in the file
        self._next_fat += 1

    def _increment_next_minifat(self):
        # Used to track the next available MINIFAT entry in the file
        self._next_minifat += 1
        if ((self._next_minifat * SIZE_FAT_ENTRY_BYTES) % self._sector_size_bytes) == 0:
            self._next_minifat = 0
            self._update_fat_by_index(self._next_fat, self._next_freesect_offset // self._sector_size_bytes)
            self._increment_next_fat()
            self._increment_next_freesect()
            self._update_fat_by_index(self._next_fat, CfbSector.EndOfChain)

    def _increment_next_directory(self):
        # Used to track the next available directory entry in a sector
        self._next_directory += SIZE_DIRECTORY_ENTRY_BYTES
        if (self._next_directory % self._sector_size_bytes) == 0:
            self._next_directory = 0
            self._update_fat_by_index(self._next_fat, self._next_freesect_offset // self._sector_size_bytes)
            self._increment_next_fat()
            self._increment_next_freesect()
            self._update_fat_by_index(self._next_fat, CfbSector.EndOfChain)

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

    def _get_sector_number(self, sector: ctypes.Structure) -> int:
        sector_offset = self._get_sector_offset(sector)
        sector_number = (sector_offset // self._sector_size_bytes) - 1
        return sector_number

    ###########################################################################
    # Header Logic
    ###########################################################################
    def _allocate_header(self):
        self._header = cHeader.from_buffer(self._data, self._next_freesect_offset)
        self._increment_next_freesect()

    def _update_header(self):
        self._header.signature = HEADER_SIGNATURE
        #self._header.clsid = HEADER_CLSID_NULL
        self._header.version_minor = HEADER_VERSION_MINOR
        self._header.version_major = HEADER_VERSION_MAJOR
        self._header.byte_order = HEADER_BYTE_ORDER
        self._header.sector_shift = SHIFT_SECTOR_BITS_V3
        self._header.mini_sector_shift = SHIFT_MINISECTOR_BITS
        self._header.sector_count_directory = 0 # Always zero for v3
        self._header.sector_count_fat = self._calc_size_fat_sectors()
        self._header.sector_start_directory = self._get_sector_number(self._directory[0])
        self._header.transaction_signature = 0
        self._header.mini_cutoff_size = SIZE_MINISTREAM_CUTOFF_BYTES

        if (len(self._minifat) > 0):
            self._header.sector_start_minifat = self._get_sector_number(self._minifat[0])
            self._header.sector_count_minifat = len(self._minifat)
        else:
            self._header.sector_start_minifat = CfbSector.EndOfChain
            self._header.sector_count_minifat = 0

        if (len(self._difat) > 0):
            self._header.sector_start_difat = self._get_sector_number(self._difat[0])
            self._header.sector_count_difat = len(self._difat)
        else:
            self._header.sector_start_difat = CfbSector.EndOfChain
            self._header.sector_count_difat = 0

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

    def _allocate_difat(self):
        self._difat: list[cDifatSector] = []
        for x in range(self._calc_size_difat_sectors()):
            # Initialize the next DIFAT sector
            new_sector = cDifatSector.from_buffer(self._data, self._next_freesect_offset)
            for y in range(self._difat_entries_per_sector): new_sector.entries[y] = CfbSector.FreeSect
            new_sector.next_difat = CfbSector.EndOfChain

            # Chain the previous DIFAT sector to this one
            if (x > 0): self._difat[x-1].next_difat = self._get_sector_number(new_sector)

            # Add it to the DIFAT list and update FAT to mark this sector as DIFSECT
            self._difat.append(new_sector)
            self._update_fat_by_index(self._get_sector_number(new_sector), CfbSector.DifSect)
            self._increment_next_fat()
            self._increment_next_freesect()

    def _update_difat(self):
        for x in range(len(self._fat)): self._update_difat_entry(x, self._get_sector_number(self._fat[x]))
        header_excess = HEADER_DIFAT_COUNT - len(self._fat)
        if (header_excess > 0):
            for x in range(header_excess): self._update_difat_entry(len(self._fat) + x, CfbSector.FreeSect)

    def _update_difat_entry(self, index: int, value: int):
        if (index < HEADER_DIFAT_COUNT):
            if VERBOSE: print(f'Setting DIFAT {index} to {value:08X} at header entry {index}')
            self._header.sector_data_difat[index] = value
        else:
            index_remainder = index - HEADER_DIFAT_COUNT
            sector_idx = index_remainder // self._difat_entries_per_sector
            entry_idx = index_remainder % self._difat_entries_per_sector
            if VERBOSE: print(f'Setting DIFAT {index} to {value:08X} at sector {sector_idx} entry {entry_idx}')
            self._difat[sector_idx].entries[entry_idx] = value

    ###########################################################################
    # FAT Logic
    ###########################################################################
    def _calc_size_fat_entries(self) -> int:
        # The FAT needs to allocate space for the directory and each file, including end-of-chains for each
        fat_entries = self._calc_size_directory_sectors() + 1 # Add one for end-of-chain ???
        for x in self._calc_size_file_sectors_by_file(): fat_entries += (x + 1) # Add one for each end-of-chain
        fat_entries += (fat_entries // self._fat_entries_per_sector) # Include overhead for the FAT sectors
        return fat_entries

    def _calc_size_fat_sectors(self) -> int:
        fat_entries = self._calc_size_fat_entries()
        fat_size_bytes = fat_entries * SIZE_FAT_ENTRY_BYTES
        fat_size_sectors = math.ceil(fat_size_bytes / self._sector_size_bytes)
        return fat_size_sectors

    def _allocate_fat(self):
        self._fat: list[cFatSector] = []
        for x in range(self._calc_size_fat_sectors()):
            new_sector = cFatSector.from_buffer(self._data, self._next_freesect_offset)
            for y in range(self._fat_entries_per_sector): new_sector.entries[y] = CfbSector.FreeSect
            self._fat.append(new_sector)
            self._update_fat_by_index(x,CfbSector.FatSect)
            self._increment_next_fat()
            self._increment_next_freesect()

    def _update_fat_by_index(self, index: int, value: int):
        if VERBOSE: print(f'Index: {index}, Value: {value:08X}')
        sector_idx = index // self._fat_entries_per_sector
        entry_idx = index % self._fat_entries_per_sector
        if VERBOSE: print(f'Setting FAT {index} to {value:08X} at sector {sector_idx} entry {entry_idx}')
        self._fat[sector_idx].entries[entry_idx] = value
        if VERBOSE: print('Success')

    ###########################################################################
    # MINIFAT Logic
    ###########################################################################
    def _calc_size_ministream_sectors_by_file(self) -> list[int]:
        sectors = []
        for stream in self._raw_input_data:
            if len(stream) < SIZE_MINISTREAM_CUTOFF_BYTES:
                sectors.append(math.ceil(len(stream)/self._sector_size_ministream_bytes))
            else:
                sectors.append(0)
        return sectors

    def _calc_size_ministream_sectors(self) -> int:
        return sum(self._calc_size_ministream_sectors_by_file())

    def _calc_size_minifat_sectors(self) -> int:
        return math.ceil(self._calc_size_ministream_sectors() * SIZE_FAT_ENTRY_BYTES/self._sector_size_bytes)

    def _allocate_minifat(self):
        self._minifat: list[cFatSector] = []
        for x in range(self._calc_size_minifat_sectors()):
            new_sector = cFatSector.from_buffer(self._data, self._next_freesect_offset)
            for y in range(self._fat_entries_per_sector): new_sector.entries[y] = CfbSector.FreeSect
            self._minifat.append(new_sector)
            self._update_fat_by_index(self._next_fat, CfbSector.EndOfChain)

            # Chain the previous MINIFAT sector to this one
            if (x > 0): self._update_fat_by_index(self._next_fat - 1, self._get_sector_number(new_sector))
            
            self._increment_next_fat()
            self._increment_next_freesect()

    def _update_minifat_by_index(self, index: int, value: int):
        if VERBOSE: print(f'Index: {index}, Value: {value:08X}')
        sector_idx = index // self._fat_entries_per_sector
        entry_idx = index % self._fat_entries_per_sector
        if VERBOSE: print(f'Setting MINIFAT {index} to {value:08X} at sector {sector_idx} entry {entry_idx}')
        self._minifat[sector_idx].entries[entry_idx] = value
        if VERBOSE: print('Success')


    ###########################################################################
    # Directory Logic
    ###########################################################################
    def _calc_size_directory_entries(self) -> int:
        # The directory tree includes a Root Entry, one entry for each file, and one entry for each folder.
        file_count = len(self._raw_input_names)
        folder_count = len(GetUniqueSubdirs(self._raw_input_paths))
        return (file_count + folder_count + 1) # Adding one for Root Directory

    def _calc_size_directory_sectors(self) -> int:
        directory_size_bytes = self._calc_size_directory_entries() * SIZE_DIRECTORY_ENTRY_BYTES
        directory_size_sectors = math.ceil(directory_size_bytes / self._sector_size_bytes)
        #raise Exception(f'dir bytes {directory_size_bytes}, sectors {directory_size_sectors}')
        return directory_size_sectors

    def _allocate_directory(self):
        # Initialize directory list
        self._directory: list[cDirEntry] = []
        self._next_directory = 0

        # Root Entry
        self._directory.append(self._allocate_directory_root())
        self._update_fat_by_index(self._next_fat, CfbSector.EndOfChain)
        self._increment_next_directory()

        # Storage (folder) and stream (file) entries
        dirs = GetFileTree(self._raw_input_paths)
        for i, x in enumerate(dirs):
            # Create this item
            if VERBOSE: print(x)
            raw_name = f'{x.name[:31]}\x00'.encode('utf-16-le') # Truncating name for now
            new_entry = cDirEntry.from_buffer(self._data, self._next_freesect_offset + self._next_directory)
            new_entry.name[:len(raw_name)] = raw_name
            new_entry.name_len_bytes = len(raw_name)
            new_entry.object_type = CfbDirType.Stream if x.is_file else CfbDirType.Storage
            new_entry.color_flag = CfbDirColor.Red
            new_entry.left_sibling_id = CfbSector.NoStream
            new_entry.right_sibling_id = CfbSector.NoStream
            new_entry.child_id = CfbSector.NoStream
            new_entry.size_bytes = len(self._raw_input_data[x.original_index]) if x.is_file else 0
            new_entry.sector_start = self._stream_start_sectors[x.original_index] - 1 if x.is_file else 0

            # Fixup parent item -- Root Entry
            if (x.parent_index is None):
                if (self._directory[0].child_id == CfbSector.NoStream):
                    if VERBOSE: print('Fixup root entry')
                    self._directory[0].child_id = i + 1
                else:
                    for j, y in enumerate(self._directory):
                        if j == 0: continue
                        if (y.right_sibling_id == CfbSector.NoStream):
                            if VERBOSE: print(f'Fixup root sibling {j}')
                            self._directory[j].right_sibling_id = i + 1
                            new_entry.left_sibling_id = j
                            break

            # Fixup parent item - user data
            if (x.parent_index is not None) and (self._directory[x.parent_index+1].child_id == CfbSector.NoStream):
                if VERBOSE: print('Fixup other entry')
                self._directory[x.parent_index+1].child_id = i + 1

            self._directory.append(new_entry)
            self._increment_next_directory()

        while (self._next_directory != 0):
            new_entry = cDirEntry.from_buffer(self._data, self._next_freesect_offset + self._next_directory)
            new_entry.object_type = CfbDirType.Unallocated
            new_entry.left_sibling_id = CfbSector.NoStream
            new_entry.right_sibling_id = CfbSector.NoStream
            new_entry.child_id = CfbSector.NoStream
            self._directory.append(new_entry)
            self._increment_next_directory()
        
        self._increment_next_fat()
        self._increment_next_freesect()
            
    def _allocate_directory_root(self) -> cDirEntry:
        raw_name = 'Root Entry\x00'.encode('utf-16-le')
        new_entry = cDirEntry.from_buffer(self._data, self._next_freesect_offset + self._next_directory)
        new_entry.name[:len(raw_name)] = raw_name
        new_entry.name_len_bytes = len(raw_name)
        new_entry.object_type = CfbDirType.RootStorage
        new_entry.color_flag = CfbDirColor.Black
        new_entry.left_sibling_id = CfbSector.NoStream
        new_entry.right_sibling_id = CfbSector.NoStream
        new_entry.child_id = CfbSector.NoStream # not supporting MINISTREAM initially, which would be pointed to here
        new_entry.clsid = (ctypes.c_byte * 16).from_buffer_copy(self._root_clsid.bytes)
        return new_entry

    ###########################################################################
    # User File Logic
    ###########################################################################
    def _calc_size_file_sectors_by_file(self) -> list[int]:
        sectors = []
        for stream in self._raw_input_data: sectors.append(math.ceil(len(stream)/self._sector_size_bytes))
        return sectors

    def _calc_size_file_sectors(self) -> int:
        return sum(self._calc_size_file_sectors_by_file())

    def _write_stream_to_fat(self, stream_data: bytes):
        view = memoryview(self._data)
        stream_size_sectors = math.ceil(len(stream_data) / self._sector_size_bytes)
        
        for x in range(stream_size_sectors):
            start = x * self._sector_size_bytes
            chunk = stream_data[start : start + self._sector_size_bytes]            
            if len(chunk) < self._sector_size_bytes: chunk = chunk.ljust(self._sector_size_bytes, b'\x00')

            offset = self._next_freesect_offset
            sector = offset // self._sector_size_bytes
            if (x > 0): self._update_fat_by_index(self._next_fat - 1, self._next_fat)
            self._update_fat_by_index(self._next_fat, CfbSector.EndOfChain)
            view[offset : offset + self._sector_size_bytes] = chunk
            self._increment_next_fat()
            self._increment_next_freesect()
    
    def _write_stream_to_minifat(self, stream_data: bytes):
        view = memoryview(self._data)
        stream_size_sectors = math.ceil(len(stream_data) / self._sector_size_ministream_bytes)

        for x in range(stream_size_sectors):
            start = x * self._sector_size_ministream_bytes
            chunk = stream_data[start : start + self._sector_size_ministream_bytes]
            if len(chunk) < self._sector_size_ministream_bytes: chunk = chunk.ljust(self._sector_size_ministream_bytes, b'\x00')

            offset = self._next_freesect_offset