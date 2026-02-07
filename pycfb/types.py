import ctypes
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
        return -1

    def init_int32(self, value: int, length: int):
        for x in range (length): self.set_int32(offset=(x*4),value=value)

    def hex_dump(self):
        return self._data.hex(' ', 4)

    @property
    def data(self) -> bytes:
        return bytes(self._data)
    
    def __repr__(self):
        return(f'Sector {self.sector_number}, Offset: {self.sector_offset}, Size: {self.sector_size}')

'''
class cHeader(ctypes.Structure):
    _pack_ = 1
    _fields = [
        ("header_signature", ctypes.c_uint64),
        ("header_clsid", ctypes.c_byte * 16),
        ("version_minor", ctypes.c_uint16),
        ("version_major", ctypes.c_uint16),
        ("byte_order", ctypes.c_uint16),
        ("sector_shift", ctypes.c_uint16),
        ("mini_sector_shift", ctypes.c_uint16),
        ("reserved", ctypes.c_byte * 6),
        ("sector_count_directory", ctypes.c_uint32),
        ("sector_count_fat", ctypes.c_uint32),
        ("sector_start_directory", ctypes.c_uint32),
        ("transaction_sig", ctypes.c_uint32),
        ("mini_cutoff_size", ctypes.c_uint32),
        ("sector_start_minifat", ctypes.c_uint32),
        ("sector_count_minifat", ctypes.c_uint32),
        ("sector_start_difat", ctypes.c_uint32),
        ("sector_count_difat", ctypes.c_uint32),
        ("sector_data_difat", ctypes.c_uint32 * 109)
    ]

class cFatSector(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("sector", ctypes.c_uint32 * 128)
    ]

class cDifatSector(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("sector", ctypes.c_uint32 * 127),
        ("next_difat", ctypes.c_uint32)
    ]

class cDirEntry(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("name", ctypes.c_char * 64),
        ("name_len_bytes", ctypes.c_uint16),
        ("object_type", ctypes.c_uint8),
        ("color_flag", ctypes.c_uint8),
        ("left_sibling_id", ctypes.c_uint32),
        ("right_sibling_id",ctypes.c_uint32),
        ("child_id", ctypes.c_uint32),
        ("clsid", ctypes.c_byte * 16),
        ("state_flags", ctypes.c_uint32),
        ("time_created", ctypes.c_uint64),
        ("time_modified", ctypes.c_uint64),
        ("sector_start", ctypes.c_uint32),
        ("size_bytes", ctypes.c_uint64),
    ]
'''

class cHeader(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("signature", ctypes.c_uint64),
        ("clsid", ctypes.c_byte * 16),
        ("version_minor", ctypes.c_uint16),
        ("version_major", ctypes.c_uint16),
        ("byte_order", ctypes.c_uint16),
        ("sector_shift", ctypes.c_uint16),
        ("mini_sector_shift", ctypes.c_uint16),
        ("reserved", ctypes.c_byte * 6),
        ("sector_count_directory", ctypes.c_uint32),
        ("sector_count_fat", ctypes.c_uint32),
        ("sector_start_directory", ctypes.c_uint32),
        ("transaction_signature", ctypes.c_uint32),
        ("mini_cutoff_size", ctypes.c_uint32),
        ("sector_start_minifat", ctypes.c_uint32),
        ("sector_count_minifat", ctypes.c_uint32),
        ("sector_start_difat", ctypes.c_uint32),
        ("sector_count_difat", ctypes.c_uint32),
        ("sector_data_difat", ctypes.c_uint32 * 109) 
    ]

    # VSCode type hints
    signature: int
    clsid: ctypes.Array[ctypes.c_byte]
    version_minor: int
    version_major: int
    byte_order: int
    sector_shift: int
    mini_sector_shift: int
    reserved: ctypes.Array[ctypes.c_byte]
    sector_count_directory: int
    sector_count_fat: int
    sector_start_directory: int
    transaction_signature: int
    mini_cutoff_size: int
    sector_start_minifat: int
    sector_count_minifat: int
    sector_start_difat: int
    sector_count_difat: int
    sector_data_difat: ctypes.Array[ctypes.c_uint32]

class cFatSector(ctypes.Structure):
    _pack_ = 1
    _fields_ = [("entries", ctypes.c_uint32 * 128)]

    # VSCode type hints
    entries: ctypes.Array[ctypes.c_uint32]

class cDifatSector(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("entries", ctypes.c_uint32 * 127),
        ("next_difat", ctypes.c_uint32)
    ]

    # VSCode type hints
    entries: ctypes.Array[ctypes.c_uint32]
    next_difat: int

class cDirEntry(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("name", ctypes.c_char * 64),
        ("name_len_bytes", ctypes.c_uint16),
        ("object_type", ctypes.c_uint8),
        ("color_flag", ctypes.c_uint8),
        ("left_sibling_id", ctypes.c_uint32),
        ("right_sibling_id", ctypes.c_uint32),
        ("child_id", ctypes.c_uint32),
        ("clsid", ctypes.c_byte * 16),
        ("state_flags", ctypes.c_uint32),
        ("time_created", ctypes.c_uint64),
        ("time_modified", ctypes.c_uint64),
        ("sector_start", ctypes.c_uint32),
        ("size_bytes", ctypes.c_uint64),
    ]

    # VSCode type hints
    name: bytes
    name_len_bytes: int
    object_type: int
    color_flag: int
    left_sibling_id: int
    right_sibling_id: int
    child_id: int
    clsid: ctypes.Array[ctypes.c_byte]
    state_flags: int
    time_created: int
    time_modified: int
    sector_start: int
    size_bytes: int