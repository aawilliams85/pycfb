from enum import IntEnum

class CfbDirType(IntEnum):
    Unallocated = 0x00
    Storage = 0x01
    Stream = 0x02
    RootStorage = 0x05

class CfbDirColor(IntEnum):
    Red = 0x0
    Black = 0x1