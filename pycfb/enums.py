from enum import IntEnum

class DirType(IntEnum):
    UNALLOCATED = 0x00
    STORAGE = 0x01
    STREAM = 0x02
    ROOTSTORAGE = 0x05

class DirColor(IntEnum):
    RED = 0x0
    BLACK = 0x1

class Sector(IntEnum):
    MINREGSECT = 0x00000000 # Minimum regular sector number
    MAXREGSECT = 0xFFFFFFFA # Maximum regular sector number
    DIFSECT = 0xFFFFFFFC    # Double Indirect FAT Sector
    FATSECT = 0xFFFFFFFD    # File Allocation Table Sector
    ENDOFCHAIN = 0xFFFFFFFE # End of Sector Chain
    FREESECT = 0xFFFFFFFF   # Free/Unallocated Sector
    NOSTREAM = 0xFFFFFFFF   # No Stream
