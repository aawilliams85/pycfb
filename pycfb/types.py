from dataclasses import dataclass

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
    sector_data_difat: list[int]        # 4 byte x 109 in header, extendable via other sectors

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