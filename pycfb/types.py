from dataclasses import dataclass, field
import struct

from pycfb import enums

@dataclass
class CfbHeader:
    header_signature: int               # 8 byte
    header_clsid: int                   # 16 byte
    version_minor: int                  # 2 byte, 0x003E if major version is 0x0003 or 0x0004
    version_major: int                  # 2 byte, 0x0003 or 0x0004
    byte_order: int                     # 2 byte
    sector_shift: int                   # 2 byte
    ministream_sector_shift: int        # 2 byte
    # reserved - 6 byte
    sector_count_directory: int         # 4 byte, always 0 in v3.
    sector_count_fat: int               # 4 byte
    sector_start_directory: int         # 4 byte
    transaction_signature_number: int   # 4 byte
    ministream_cutoff_size: int         # 4 byte
    sector_start_minifat: int           # 4 byte
    sector_count_minifat: int           # 4 byte
    sector_start_difat: int             # 4 byte
    sector_count_difat: int             # 4 byte
    sector_data_difat: list[int] = field(repr=False) # 4 byte x 109 in header, extendable via other sectors

@dataclass
class CfbDirEntry:
    name: str                   # 64 byte, UTF-16 LE (null terminated)
    name_len_bytes: int         # 2 byte
    type: enums.CfbDirType      # 1 byte
    color: enums.CfbDirColor    # 1 byte
    sibling_id_left: int        # 4 byte
    sibling_id_right: int       # 4 byte
    child_id: int               # 4 byte
    clsid: int                  # 16 byte
    state: int                  # 4 byte
    time_created: int           # 8 byte, Windows FILETIME in UTC
    time_modified: int          # 8 byte, Windows FILETIME in UTC
    sector_start: int           # 4 byte
    size_bytes: int             # 8 byte

class CfbMappedSector:
    def __init__(self, sector_size: int, sector_number: int, sector_offset: int):
        self.sector_size = sector_size
        self.sector_number = sector_number
        self.sector_offset = sector_offset
        self._data = bytearray(self.sector_size)
        self._intformat = '<I'

    def set_int32(self, offset: int, value: int):
        if not (0 <= offset <= self.sector_size - 4): raise IndexError(f'Offset {offset} out of range.')
        struct.pack_into(self._intformat, self._data, offset, value)

    def get_int32(self, offset: int):
        if not (0 <= offset <= self.sector_size - 4): raise IndexError(f'Offset {offset} out of range.')
        return struct.unpack_from(self._intformat, self._data, offset)[0]

    def seek_int32(self, value: int) -> int:
        for x in range(self.sector_size / 4):
            offset = x * 4
            y = struct.unpack_from(self._intformat, self._data, offset)[0]
            if (y == value): return offset
        raise ValueError(f'Failed to find value {value} in buffer.')

    def hex_dump(self):
        return self._data.hex(' ', 4)

    @property
    def data(self) -> bytes:
        return bytes(self._data)
    
    def __repr__(self):
        return(f'Sector {self.sector_number}, Offset: {self.sector_offset}, Size: {self.sector_size}')
    
class CfbMappedDifsect(CfbMappedSector):
    pass