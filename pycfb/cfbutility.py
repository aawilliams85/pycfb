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
        # First create header with initial values that can be expanded later
        #
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
            sector_count_fat=0,
            sector_start_directory=1, # always 1
            transaction_signature_number=0,
            ministream_cutoff_size=SIZE_MINISTREAM_CUTOFF_BYTES,
            sector_start_minifat=CfbSector.EndOfChain, # not supporting MINISTREAM initially, so MINIFAT is not needed
            sector_count_minifat=0,
            sector_start_difat=CfbSector.EndOfChain, # until DIFAT needs to be expanded, it ends with the header entries
            sector_count_difat=0,
            sector_data_difat=self._init_difat(HEADER_DIFAT_COUNT)
        )
        self._sector_size_bytes = 2**(self._header.sector_shift)
        self._sector_size_ministream_bytes = 2**(self._header.ministream_sector_shift)

        # Ingest raw streams
        self._raw_stream_names = stream_names
        self._raw_stream_paths = stream_paths
        self._raw_stream_data = stream_data

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
        for stream in self._raw_stream_data:
            pass

        #print(self._header)
        #print(self._sector_size_bytes)
        #print(self._sector_size_ministream_bytes)
        #print(self._raw_stream_names)
        #print(self._raw_stream_data)
        print(self._root_directory)
        print(self._calc_size_minifat_sectors())
        print(self._calc_size_ministream_sectors())
        print(self._calc_size_directory_sectors())
        print(self._calc_size_file_sectors())
        print(self._calc_size_fat_sectors())
        print(self._calc_size_difat_sectors())

    def _init_difat(self, size: int) -> list[int]: return [CfbSector.FreeSect] * size

    # Try to estimate how much space will be required to allocate
    def _calc_size_ministream_sectors(self) -> int:
        # Not supporting MINISTREAM initially
        return 0
    def _calc_size_minifat_sectors(self) -> int:
        # Not supporting MINIFAT initially
        return 0
    def _calc_size_directory_sectors(self) -> int:
        # The directory tree includes a Root Entry, one entry for each file, and one entry for each folder.
        file_count = len(self._raw_stream_names)
        folder_count = len(GetUniqueSubdirs(self._raw_stream_names))
        directory_size_bytes = (file_count + folder_count + 1) * SIZE_DIRECTORY_ENTRY_BYTES # Adding one for Root Directory
        directory_size_sectors = math.ceil(directory_size_bytes / self._sector_size_bytes)
        return directory_size_sectors
    def _calc_size_file_sectors_by_file(self) -> list[int]:
        sectors = []
        for stream in self._raw_stream_data: sectors.append(math.ceil(len(stream)/self._sector_size_bytes))
        return sectors
    def _calc_size_file_sectors(self) -> int:
        return sum(self._calc_size_file_sectors_by_file())
    def _calc_size_fat_sectors(self) -> int:
        # The FAT needs to allocate space for the directory and each file, including end-of-chains for each
        fat_entries = self._calc_size_directory_sectors() + 1 # Add one for end-of-chain ???
        for x in self._calc_size_file_sectors_by_file(): fat_entries += (x + 1) # Add one for each end-of-chain
        fat_size_bytes = fat_entries * SIZE_FAT_ENTRY_BYTES
        fat_size_sectors = math.ceil(fat_size_bytes / self._sector_size_bytes)
        return fat_size_sectors
    def _calc_size_difat_sectors(self) -> int:
        # The DIFAT needs to allocate space for the FAT if it exceeds the 109 entries available in the header
        difat_entries = self._calc_size_fat_sectors() + 1 # Add one for end-of-chain ???
        difat_size_bytes = (difat_entries - HEADER_DIFAT_COUNT) * SIZE_DIFAT_ENTRY_BYTES
        if (difat_size_bytes < 0): difat_size_bytes = 0
        difat_size_sectors = math.ceil(difat_size_bytes / self._sector_size_bytes)
        return difat_size_sectors