# Header Constants
HEADER_SIGNATURE = 0xE11AB1A1E011CFD0                   # OLE2 file signature
HEADER_CLSID_NULL = 0x00000000000000000000000000000000  # Null ClassID
HEADER_VERSION_MAJOR = 0x0003                           #
HEADER_VERSION_MINOR = 0x003E                           #
HEADER_BYTE_ORDER = 0xFFFE                              # Little Endian byte-order mark
HEADER_DIFAT_COUNT = 109                                # The first 109 entries of DIFAT are always in the header

# Special Sector Values
# SECTOR_REGSECT 0x00000000-0xFFFFFFF9 # Regular sector
SECTOR_MAXREGSECT = 0xFFFFFFFA         # Maximum regular sector number
SECTOR_DIFSECT = 0xFFFFFFFC            # Specifies a DIFAT sector in the FAR
SECTOR_FATSECT = 0xFFFFFFFD            # Specifies a FAT sector in the FAT
SECTOR_ENDOFCHAIN = 0xFFFFFFFE         # End of linked chain of sectors
SECTOR_FREESECT = 0xFFFFFFFF           # Specifies unallocated sector in the FAT, Mini FAT, or DIFAT

# Sizes and byte shifts
SHIFT_MINISECTOR_BITS = 0x0006
SHIFT_SECTOR_BITS_V3 = 0x0009
SHIFT_SECTOR_BITS_V4 = 0x000C
SIZE_DIFAT_BYTES = 4
SIZE_DIRECTORY_BYTES = 128
SIZE_FAT_BYTES = 4
SIZE_MINIFAT_BYTES = 4
SIZE_MINISTREAM_CUTOFF_BYTES = 4096
SIZE_SECTOR_BYTES_V3 = 512
SIZE_SECTOR_BYTES_V4 = 4096