from enum import IntEnum

class CfbDirType(IntEnum):
    Unallocated = 0x00
    Storage = 0x01
    Stream = 0x02
    RootStorage = 0x05

class CfbDirColor(IntEnum):
    Red = 0x0
    Black = 0x1

class CfbSector(IntEnum):
    MinRegSect = 0x00000000 # Minimum regular sector number
    MaxRegSect = 0xFFFFFFFA # Maximum regular sector number
    DifSect = 0xFFFFFFFC    # Double Indirect FAT Sector
    FatSect = 0xFFFFFFFD    # File Allocation Table Sector
    EndOfChain = 0xFFFFFFFE # End of Sector Chain
    FreeSect = 0xFFFFFFFF   # Free/Unallocated Sector