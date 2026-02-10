# Header Constants
HEADER_SIGNATURE = 0xE11AB1A1E011CFD0                   # OLE2 file signature
HEADER_CLSID_NULL = 0x00000000000000000000000000000000  # Null ClassID
HEADER_VERSION_MAJOR = 0x0003                           #
HEADER_VERSION_MINOR = 0x003E                           #
HEADER_BYTE_ORDER = 0xFFFE                              # Little Endian byte-order mark
HEADER_DIFAT_COUNT = 109                                # The first 109 entries of DIFAT are always in the header

# Bit shifts
SHIFT_MINISECTOR_BITS = 0x0006  # 64 byte
SHIFT_SECTOR_BITS_V3 = 0x0009   # 512 byte
SHIFT_SECTOR_BITS_V4 = 0x000C   # 4096 byte

# Entry Sizes
SIZE_DIFAT_ENTRY_BYTES = 4
SIZE_DIRECTORY_ENTRY_BYTES = 128
SIZE_FAT_ENTRY_BYTES = 4
SIZE_MINIFAT_ENTRY_BYTES = 4
SIZE_MINISTREAM_CUTOFF_BYTES = 4096