import math
import uuid

from pycfb import constants
from pycfb import enums
from pycfb import types

class CFBWriter:
    def __init__(
        self,
        stream_names: list[str],
        stream_data: list[bytes],
        root_clsid: uuid.UUID
    ):
        # First create header with initial values that can be expanded later
        #
        # Keep in mind that the header is treated like "sector -1" even though it is
        # the beginning of the file.  So a directory starting at sector 1 is an offset
        # of 1024 bytes.
        self._header = types.CfbHeader(
            header_signature=constants.HEADER_SIGNATURE,
            header_clsid=constants.HEADER_CLSID_NULL,
            version_minor=constants.HEADER_VERSION_MINOR,
            version_major=constants.HEADER_VERSION_MAJOR,
            byte_order=constants.HEADER_BYTE_ORDER,
            sector_shift=constants.SHIFT_SECTOR_BITS_V3, # only targeting V3
            ministream_sector_shift=constants.SHIFT_MINISECTOR_BITS,
            sector_count_directory=0, # always 0 for V3
            sector_count_fat=0,
            sector_start_directory=1, # always 1
            transaction_signature_number=0,
            ministream_cutoff_size=constants.SIZE_MINISTREAM_CUTOFF_BYTES,
            sector_start_minifat=constants.SECTOR_ENDOFCHAIN, # not supporting MINIFAT initially
            sector_count_minifat=0,
            sector_start_difat=constants.SECTOR_ENDOFCHAIN, # until DIFAT needs to be expanded, it ends with the header entries
            sector_count_difat=0,
            sector_data_difat=self._init_difat(constants.HEADER_DIFAT_COUNT)
        )
        self._sector_size_bytes = 2**(self._header.sector_shift)
        self._sector_size_ministream_bytes = 2**(self._header.ministream_sector_shift)

        # Ingest raw streams
        self._raw_stream_names = stream_names
        self._raw_stream_data = stream_data
        self._raw_stream_sectors = self._estimate_fat_sector_count()
        self._raw_stream_total_sectors = sum(self._raw_stream_sectors)

        # Create Root Directory entry
        self._root_directory = types.CfbDirEntry(
            name='Root Entry',
            name_len_bytes=22,
            type=enums.CfbDirType.RootStorage,
            color=enums.CfbDirColor.Red,
            sibling_id_left=constants.SECTOR_FREESECT,
            sibling_id_right=constants.SECTOR_FREESECT,
            child_id=0, # will be specified later
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
        print(self._raw_stream_sectors)
        print(self._raw_stream_total_sectors)
        print(self._root_directory)

    def _init_difat(self, size: int) -> list[int]: return [constants.SECTOR_FREESECT] * size
    def _estimate_fat_sector_count(self) -> int:
        sectors = []
        for stream in self._raw_stream_data: sectors.append(math.ceil(len(stream)/self._sector_size_bytes))
        return sectors