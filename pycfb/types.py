import ctypes

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